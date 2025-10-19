# app.py
import os
import re
import unicodedata

from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Chat, Interaction
from ai_client import get_ai_reply_responses_api  # uses Responses API (v5-style)

# -----------------------------------------------------------------------------
# App & Config
# -----------------------------------------------------------------------------
load_dotenv()

app = Flask(__name__, static_url_path="", static_folder=".")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")  # cookie signing
CORS(app)

# Show safety notice once per server start (and per browser via cookie)
SHOWN_NOTICE = False

# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------
DB_URL = "sqlite:///chat_log.db"
engine = create_engine(DB_URL, echo=False, future=True)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def classify_risk(text: str) -> str:
    """Heuristic keyword/phrase classifier with English + JA variants."""
    import re as _re
    import unicodedata as _ud

    t = (text or "")
    t = t.replace("’", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    t = _ud.normalize("NFKC", t).lower()
    t = _re.sub(r"\s+", " ", t.strip())

    low = {
        "happy","good","fine","okay","ok","great","alright","all right","cool","blessed",
        "i'm good","im good","i am good","i'm fine","im fine","i am fine",
        "i'm okay","im okay","i am okay","can't complain","cant complain",
        "mi good","mi deh yah","deh yah","mi irie","irie","mi alright","mi alrite","mi alr",
        "😊","🙂","👍","👌","bless up","no problem","np"
    }
    med = {
        "sad","down","low","blue","anxious","anxiety","worried","worry","stressed","stress",
        "tired","exhausted","burnt out","burned out","overwhelmed","overwhelm","lonely","alone",
        "angry","frustrated","mixed feelings","not great","not okay","not ok","meh",
        "struggling","having a hard time","not feeling like myself","drained","can't focus","cant focus",
        "can't sleep","cant sleep","insomnia",
        "mi tired","mi stress","mi stress out","mi mash up","mi nuh too good","mi nah manage",
        "head a hurt mi","mi spirit low","mi nah feel like miself","mi feel away",
        "😕","🙁","😟","😞","🥺","💤","😴"
    }
    high = {
        "suicidal","suicide","i want to die","i wanna die","i want die","wish i were dead","wish i was dead",
        "i'm done with life","im done with life","done with life","life not worth it","life isn't worth it",
        "nothing is worth it anymore","nothing matters anymore","i can't go on","cant go on",
        "i'm going to kill myself","im going to kill myself","kill myself","end my life","end it all",
        "self harm","self-harm","cut myself","hurt myself","overdose","od","take my life",
        "hopeless","worthless","no reason to live","i see no way out","i give up",
        "mi cyah badda","mi cyaan badda","mi cyaa badda","mi cyan badda","mi cah badda","mi cyaa manage",
        "mi tired a life","mi tyad a life","mi done wid life","mi done with life","mi feel fi dead",
        "mi nuh waan live","mi noh waan live","mi no waan live","mi waan done","mi feel fi end it",
        "mi cyaan tek dis","mi cyan tek dis","mi can't take this","cant take this anymore","mi cyah badda",
        "goodbye everyone","this is my last message","you won't hear from me again","i won't be here tomorrow",
        "🪦","🔪","💊","🩸"
    }

    def contains_any(h: str, terms: set[str]) -> bool:
        phrases = [w for w in terms if " " in w or any(ch in w for ch in "🪦🔪💊🩸")]
        singles  = [w for w in terms if w not in phrases]
        for p in phrases:
            if p in h:
                return True
        for s in singles:
            if len(s) <= 2 or any(ch in s for ch in "🪦🔪💊🩸"):
                if s in h:
                    return True
                continue
            if re.search(rf"\b{re.escape(s)}\b", h):
                return True
        return False

    if contains_any(t, high):   return "high"
    if contains_any(t, med):    return "medium"
    if contains_any(t, low):    return "low"
    return "low"

SAFETY_NOTE_JM = (
    "Remember, if you’re in immediate danger, call 119 (Police) or 110 (Ambulance/Fire) now.\n\n"
    "For mental health or emotional support:\n"
    "• SafeSpot JA (children & teens): 876-439-5199 or 888-723-3776\n"
    "• U-Matter (youth chatline): Message “SUPPORT” to 876-838-4897 via WhatsApp or SMS\n"
    "• Mental Health & Suicide Prevention Helpline: 888-639-5433 (888-NEW-LIFE)"
)

MONITORING_NOTICE_JM = (
    "Safety notice: This conversation is automatically screened for crisis language so we can help keep you safe. "
    "If high-risk phrases are detected, we may notify a designated helpline and share the minimum necessary information "
    "to assist you. If you’re in immediate danger, call 119 (Police) or 110 (Ambulance/Fire)."
)

def log_interaction(s, chat_id: int, user_message: str, bot_reply: str, risk_level: str) -> None:
    s.add(Interaction(
        chat_id=chat_id,
        user_message=user_message,
        bot_reply=bot_reply,
        risk_level=risk_level,
    ))
    s.commit()

def get_or_create_chat(s) -> Chat:
    """Find the chat via cookie; if missing or stale, create one."""
    cid = request.cookies.get("chat_id")
    chat = None
    if cid and cid.isdigit():
        chat = s.get(Chat, int(cid))
    if not chat:
        chat = Chat()
        s.add(chat)
        s.commit()
    return chat

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    return send_file("index.html")

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"ok": True})

@app.route("/test", methods=["GET"])
def test():
    return jsonify({"message": "Server running"})

@app.route("/reset", methods=["POST"])
def reset():
    s = Session()
    try:
        chat = get_or_create_chat(s)
        s.query(Interaction).filter(Interaction.chat_id == chat.id).delete()
        s.commit()
        resp = jsonify({"ok": True, "message": "Chat reset."})
        resp.set_cookie("chat_id", str(chat.id), max_age=60*60*24*30, httponly=False, samesite="Lax")
        return resp
    except Exception as e:
        s.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500
    finally:
        s.close()

@app.route("/chat", methods=["POST"])
def chat():
    global SHOWN_NOTICE

    data = request.get_json(silent=True) or {}
    user_msg = (data.get("message") or "").strip()
    if not user_msg:
        return jsonify({"reply": "Please type a message.", "risk": "low"})

    s = Session()
    try:
        # Ensure we have a chat row for this browser
        chat_row = get_or_create_chat(s)

        # One-time monitoring notice per server start + per browser
        seen_cookie = request.cookies.get("seen_notice") == "1"
        show_notice = (not SHOWN_NOTICE) and (not seen_cookie)

        risk = classify_risk(user_msg)

        # --- Call OpenAI (Responses API helper) ---
        assistant_text = get_ai_reply_responses_api(user_msg)

        # Prepend one-time monitoring notice
        if show_notice:
            assistant_text = MONITORING_NOTICE_JM + "\n\n" + assistant_text
            SHOWN_NOTICE = True

        # Append local safety note for high-risk cases (Jamaica)
        if risk == "high":
            assistant_text += " " + SAFETY_NOTE_JM

        # Save
        log_interaction(s, chat_row.id, user_msg, assistant_text, risk)

        # Build response + set cookies (chat_id + seen_notice)
        resp = jsonify({"reply": assistant_text, "risk": risk})
        resp.set_cookie("chat_id", str(chat_row.id), max_age=60*60*24*30, httponly=False, samesite="Lax")
        if show_notice:
            resp.set_cookie("seen_notice", "1", max_age=60*60*24*30, httponly=False, samesite="Lax")
        return resp
    finally:
        s.close()

@app.route("/send", methods=["POST"])
def send_message_route():
    """
    Optional alias: same behavior as /chat, for frontends that POST to /send.
    """
    # Reuse the /chat logic so you keep logging / safety / cookies consistent.
    return chat()

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
