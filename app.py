from flask import (Flask, request, redirect, render_template,
                   jsonify, abort, session, url_for, flash)
import sqlite3, string, random, bcrypt, os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production-please")
DB = "urls.db"

# ── DB setup ────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                email    TEXT    NOT NULL UNIQUE,
                password TEXT    NOT NULL,
                created  TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id  INTEGER NOT NULL,
                original TEXT    NOT NULL,
                short    TEXT    NOT NULL UNIQUE,
                clicks   INTEGER DEFAULT 0,
                created  TEXT    NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()

# ── Auth helpers ─────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def current_user():
    if "user_id" not in session:
        return None
    with get_db() as conn:
        return conn.execute(
            "SELECT id, email FROM users WHERE id=?", (session["user_id"],)
        ).fetchone()

# ── Code generator ────────────────────────────────────────────────
def make_code():
    chars = string.ascii_letters + string.digits
    for _ in range(10):
        code = ''.join(random.choices(chars, k=6))
        with get_db() as conn:
            if not conn.execute("SELECT 1 FROM urls WHERE short=?", (code,)).fetchone():
                return code
    raise RuntimeError("Could not generate unique code")

# ── Routes: Auth ─────────────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")

        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("register.html")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html")
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO users (email, password, created) VALUES (?,?,?)",
                    (email, hashed, datetime.now().strftime("%Y-%m-%d %H:%M"))
                )
                conn.commit()
                user = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
                session["user_id"]    = user["id"]
                session["user_email"] = email
            return redirect(url_for("index"))
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "error")
            return render_template("register.html")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE email=?", (email,)
            ).fetchone()

        if user and bcrypt.checkpw(password.encode(), user["password"].encode()):
            session["user_id"]    = user["id"]
            session["user_email"] = user["email"]
            return redirect(url_for("index"))
        else:
            flash("Invalid email or password.", "error")
            return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Routes: App ──────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    with get_db() as conn:
        recent = [dict(r) for r in conn.execute(
            "SELECT * FROM urls WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (session["user_id"],)
        ).fetchall()]
    return render_template("index.html", recent=recent,
                           user_email=session.get("user_email", ""))


@app.route("/shorten", methods=["POST"])
@login_required
def shorten():
    data     = request.get_json()
    original = data.get("url", "").strip()

    if not original:
        return jsonify({"error": "URL is required"}), 400
    if not original.startswith(("http://", "https://")):
        original = "https://" + original

    with get_db() as conn:
        existing = conn.execute(
            "SELECT short FROM urls WHERE original=? AND user_id=?",
            (original, session["user_id"])
        ).fetchone()
        if existing:
            short = existing["short"]
        else:
            short = make_code()
            conn.execute(
                "INSERT INTO urls (user_id, original, short, clicks, created) VALUES (?,?,?,0,?)",
                (session["user_id"], original, short,
                 datetime.now().strftime("%Y-%m-%d %H:%M"))
            )
            conn.commit()

    base = request.host_url.rstrip("/")
    return jsonify({"short_url": f"{base}/{short}", "code": short})


@app.route("/<code>")
def redirect_url(code):
    with get_db() as conn:
        row = conn.execute("SELECT original FROM urls WHERE short=?", (code,)).fetchone()
        if not row:
            abort(404)
        conn.execute("UPDATE urls SET clicks = clicks + 1 WHERE short=?", (code,))
        conn.commit()
    return redirect(row["original"])


@app.route("/stats/<code>")
@login_required
def stats(code):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM urls WHERE short=? AND user_id=?",
            (code, session["user_id"])
        ).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify(dict(row))


@app.route("/delete/<code>", methods=["POST"])
@login_required
def delete_link(code):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM urls WHERE short=? AND user_id=?",
            (code, session["user_id"])
        )
        conn.commit()
    return jsonify({"success": True})


@app.route("/api/all")
@login_required
def all_urls():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM urls WHERE user_id=? ORDER BY id DESC",
            (session["user_id"],)
        ).fetchall()
    return jsonify([dict(r) for r in rows])

init_db()
if __name__ == "__main__":
    
    app.run(debug=True)
