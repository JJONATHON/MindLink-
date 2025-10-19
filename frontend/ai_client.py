# ai_client.py
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

def get_ai_reply_responses_api(user_msg: str) -> str:
    """
    Calls the Responses API (v5-style) and returns a plain text reply.
    Use a model you know you have access to (gpt-4o-mini is widely available).
    """
    if not client.api_key:
        return "(Demo) No API key configured."

    try:
        resp = client.responses.create(
            model="gpt-4o-mini",   # change only after you verify access to another model
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are a supportive mental health friend for the user. "
                        "Be kind, friendly and don't misguide the user. Use emojis to lighten the conversation. "
                        "Organize each response in short paragraphs with clear spacing. "
                        "Split responses roughly every 2 sentences to avoid overwhelming the user."
                    ),
                },
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
            max_output_tokens=400,
        )

        # Newer SDKs expose this:
        text = getattr(resp, "output_text", None)
        if text:
            return text.strip()

        # Fallback parse for older Responses builds:
        chunks = []
        for part in getattr(resp, "output", []) or []:
            for c in getattr(part, "content", []) or []:
                if getattr(c, "type", "") == "output_text":
                    chunks.append(getattr(c, "text", ""))
        return ("".join(chunks)).strip() or "(Fallback) No text returned."

    except Exception as e:
        print("OpenAI error:", repr(e))
        return "(Fallback) I’m here with you. I couldn’t reach the model just now."
