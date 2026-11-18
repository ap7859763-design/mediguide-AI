import os
import re
from functools import wraps
from contextlib import contextmanager

import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.security import check_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-development-secret")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "false").lower() == "true",
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")

SYSTEM_PROMPT = """
You are MediGuide AI, an educational medical information assistant.
Explain general health information in simple Hindi or English.
Do not diagnose, prescribe medicines or dosages, or advise starting/stopping medication.
Do not claim that a symptom proves a particular disease.
For severe or rapidly worsening symptoms, advise immediate professional medical help.
In India, the emergency number is 112.
Be clear that your information is educational and not a substitute for a qualified clinician.
"""


@contextmanager
def db_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "mediguide_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        port=os.getenv("DB_PORT", "5432"),
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_logged_in"):
            if request.path.startswith("/api/admin"):
                return jsonify({"error": "Admin login required"}), 401
            return redirect(url_for("admin_login"))
        return fn(*args, **kwargs)
    return wrapper


def fetch_all(sql, params=()):
    with db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def fetch_one(sql, params=()):
    with db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def clean_text(value, limit=5000):
    return str(value or "").strip()[:limit]


@app.route("/")
def home():
    try:
        stats = {
            "diseases": fetch_one("SELECT COUNT(*) AS count FROM diseases")["count"],
            "faqs": fetch_one("SELECT COUNT(*) AS count FROM faq")["count"],
        }
    except Exception:
        stats = {"diseases": 0, "faqs": 0}
    return render_template(
        "index.html",
        stats=stats,
        admin_logged_in=session.get("admin_logged_in", False)
    )


@app.get("/api/diseases")
def api_diseases():
    q = clean_text(request.args.get("q"), 120)
    if q:
        like = f"%{q}%"
        rows = fetch_all("""
            SELECT id, name, category, description, symptoms, causes, prevention, care
            FROM diseases
            WHERE name ILIKE %s OR category ILIKE %s OR description ILIKE %s
               OR symptoms ILIKE %s
            ORDER BY name
        """, (like, like, like, like))
    else:
        rows = fetch_all("""
            SELECT id, name, category, description, symptoms, causes, prevention, care
            FROM diseases ORDER BY name
        """)
    return jsonify(rows)


@app.get("/api/faqs")
def api_faqs():
    return jsonify(fetch_all(
        "SELECT id, question, answer, category FROM faq ORDER BY id DESC"
    ))


@app.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = clean_text(data.get("message"), 1200)
    language = data.get("language", "en-IN")

    if not message:
        return jsonify({"reply": "Please enter a question."}), 400

    lower = message.lower()
    urgent_terms = [
        "can't breathe", "cannot breathe", "difficulty breathing",
        "severe bleeding", "unconscious", "seizure", "stroke symptoms"
    ]

    if any(term in lower for term in urgent_terms):
        return jsonify({
            "reply": (
                "This may be an emergency. Please seek immediate medical help. "
                "In India, call 112 or go to the nearest emergency department. "
                "Do not wait for a chatbot response."
            ),
            "source": "Safety guidance"
        })

    diseases = fetch_all("""
        SELECT name, category, description, symptoms, causes, prevention, care
        FROM diseases ORDER BY LENGTH(name) DESC
    """)

    for d in diseases:
        if d["name"].lower() in lower:
            reply = (
                f'{d["name"]} ({d["category"]})\\n\\n'
                f'Introduction: {d["description"]}\\n'
                f'Possible symptoms: {d["symptoms"]}\\n'
                f'Possible causes: {d["causes"]}\\n'
                f'Prevention: {d["prevention"]}\\n'
                f'General care: {d["care"]}\\n\\n'
                'Educational information only. This is not a diagnosis or treatment plan.'
            )
            return jsonify({
                "reply": reply,
                "source": "PostgreSQL Disease Library"
            })

    faqs = fetch_all("SELECT question, answer FROM faq")
    words = {w for w in re.findall(r"[a-zA-Z]{3,}", lower)}
    best, best_score = None, 0

    for faq in faqs:
        qwords = set(re.findall(r"[a-zA-Z]{3,}", faq["question"].lower()))
        score = len(words & qwords) / max(len(words), 1)
        if score > best_score:
            best, best_score = faq, score

    if best and best_score >= 0.5:
        return jsonify({
            "reply": best["answer"],
            "source": "PostgreSQL FAQ"
        })

    prompt_language = "simple Hindi" if language == "hi-IN" else "simple English"

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "stream": False,
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT + f" Reply in {prompt_language}."
                    },
                    {"role": "user", "content": message},
                ],
            },
            timeout=60,
        )
        response.raise_for_status()
        answer = response.json().get("message", {}).get("content", "").strip()

        if not answer:
            raise ValueError("Empty response from Ollama")

        return jsonify({
            "reply": answer + (
                "\n\nEducational information only. Please consult a qualified "
                "healthcare professional for personal medical concerns."
            ),
            "source": "Ollama AI",
        })

    except (requests.RequestException, ValueError) as exc:
        app.logger.warning("Ollama unavailable: %s", exc)
        return jsonify({
            "reply": (
                "I could not find a matching entry in the local database and "
                "the AI service is unavailable. Please try again later or "
                "consult a qualified healthcare professional."
            ),
            "source": "Unavailable",
        }), 503


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin"))

    if request.method == "POST":
        username = clean_text(request.form.get("username"), 80)
        password = request.form.get("password", "")

        if not ADMIN_PASSWORD_HASH:
            flash(
                "Admin password is not configured. Set ADMIN_PASSWORD_HASH in .env.",
                "error"
            )
        elif (
            username == ADMIN_USERNAME
            and check_password_hash(ADMIN_PASSWORD_HASH, password)
        ):
            session.clear()
            session["admin_logged_in"] = True
            session["admin_username"] = username
            return redirect(url_for("admin"))
        else:
            flash("Invalid username or password.", "error")

    return render_template("admin_login.html")


@app.get("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))


@app.get("/admin")
@admin_required
def admin():
    stats = {
        "diseases": fetch_one("SELECT COUNT(*) AS count FROM diseases")["count"],
        "faqs": fetch_one("SELECT COUNT(*) AS count FROM faq")["count"],
    }
    diseases = fetch_all("SELECT * FROM diseases ORDER BY name")
    faqs = fetch_all("SELECT * FROM faq ORDER BY id DESC")

    return render_template(
        "admin.html",
        stats=stats,
        diseases=diseases,
        faqs=faqs
    )


@app.post("/api/admin/diseases")
@admin_required
def admin_add_disease():
    data = request.get_json(silent=True) or {}
    name = clean_text(data.get("name"), 150)

    if not name:
        return jsonify({"error": "Disease name is required"}), 400

    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO diseases
                (name, category, description, symptoms, causes, prevention, care)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                name,
                clean_text(data.get("category"), 100),
                clean_text(data.get("description")),
                clean_text(data.get("symptoms")),
                clean_text(data.get("causes")),
                clean_text(data.get("prevention")),
                clean_text(data.get("care")),
            ))

    return jsonify({"message": "Disease added"}), 201


@app.put("/api/admin/diseases/<int:item_id>")
@admin_required
def admin_update_disease(item_id):
    data = request.get_json(silent=True) or {}
    name = clean_text(data.get("name"), 150)

    if not name:
        return jsonify({"error": "Disease name is required"}), 400

    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE diseases SET name=%s, category=%s, description=%s,
                symptoms=%s, causes=%s, prevention=%s, care=%s
                WHERE id=%s
            """, (
                name,
                clean_text(data.get("category"), 100),
                clean_text(data.get("description")),
                clean_text(data.get("symptoms")),
                clean_text(data.get("causes")),
                clean_text(data.get("prevention")),
                clean_text(data.get("care")),
                item_id,
            ))

            if cur.rowcount == 0:
                return jsonify({"error": "Disease not found"}), 404

    return jsonify({"message": "Disease updated"})


@app.delete("/api/admin/diseases/<int:item_id>")
@admin_required
def admin_delete_disease(item_id):
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM diseases WHERE id=%s", (item_id,))
            if cur.rowcount == 0:
                return jsonify({"error": "Disease not found"}), 404

    return jsonify({"message": "Disease deleted"})


@app.post("/api/admin/faqs")
@admin_required
def admin_add_faq():
    data = request.get_json(silent=True) or {}
    question = clean_text(data.get("question"), 1000)
    answer = clean_text(data.get("answer"))

    if not question or not answer:
        return jsonify({"error": "Question and answer are required"}), 400

    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO faq (question, answer, category) VALUES (%s,%s,%s)",
                (
                    question,
                    answer,
                    clean_text(data.get("category"), 100)
                ),
            )

    return jsonify({"message": "FAQ added"}), 201


@app.put("/api/admin/faqs/<int:item_id>")
@admin_required
def admin_update_faq(item_id):
    data = request.get_json(silent=True) or {}
    question = clean_text(data.get("question"), 1000)
    answer = clean_text(data.get("answer"))

    if not question or not answer:
        return jsonify({"error": "Question and answer are required"}), 400

    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE faq SET question=%s, answer=%s, category=%s WHERE id=%s",
                (
                    question,
                    answer,
                    clean_text(data.get("category"), 100),
                    item_id
                ),
            )

            if cur.rowcount == 0:
                return jsonify({"error": "FAQ not found"}), 404

    return jsonify({"message": "FAQ updated"})


@app.delete("/api/admin/faqs/<int:item_id>")
@admin_required
def admin_delete_faq(item_id):
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM faq WHERE id=%s", (item_id,))
            if cur.rowcount == 0:
                return jsonify({"error": "FAQ not found"}), 404

    return jsonify({"message": "FAQ deleted"})


@app.errorhandler(psycopg2.Error)
def handle_db_error(error):
    app.logger.exception("Database error")

    if request.path.startswith("/api/"):
        return jsonify({
            "error": "Database error. Check PostgreSQL settings and run init_db.py."
        }), 500

    return "Database error. Check PostgreSQL settings and run init_db.py.", 500


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")