import os
import json
from gtts import gTTS
from flask import Flask, render_template, request, send_from_directory, jsonify
import google.generativeai as genai
from dotenv import load_dotenv

# =========================
# CONFIG
# =========================
NOTES_FILE = "notes_db.json"
AUDIO_DIR = "audio_notes"
LANGUAGE = "en"
MODEL_NAME = "gemini-2.0-flash"

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("❌ GOOGLE_API_KEY not found in .env file")

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

# Flask setup
app = Flask(__name__)
os.makedirs(AUDIO_DIR, exist_ok=True)


# =========================
# Utilities
# =========================
def load_notes():
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, "r") as f:
            return json.load(f)
    return []


def save_notes(notes):
    with open(NOTES_FILE, "w") as f:
        json.dump(notes, f, indent=2)


def generate_summary_with_gemini(text: str) -> str:
    try:
        prompt = f"Summarize this text in 2-3 sentences:\n\n{text}"
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except Exception as e:
        print(f"⚠️ Error generating summary: {e}")
        return None


def text_to_speech(text, filename):
    tts = gTTS(text=text, lang=LANGUAGE, slow=False)
    tts.save(filename)


# =========================
# Flask Routes
# =========================
@app.route("/", methods=["GET", "POST"])
def index():
    notes = load_notes()
    if request.method == "POST":
        text = request.form.get("note_text", "").strip()
        tags = request.form.get("tags", "").split(",")
        tags = [t.strip() for t in tags if t.strip()]
        use_summary = request.form.get("summary") == "on"

        if not text:
            return render_template("index.html", notes=notes, error="Note text cannot be empty.")

        summary = generate_summary_with_gemini(text) if use_summary else None

        note_id = len(notes) + 1
        audio_file = os.path.join(AUDIO_DIR, f"note_{note_id}.mp3")
        text_to_speech(text, audio_file)

        note_entry = {
            "id": note_id,
            "text": text,
            "summary": summary,
            "tags": tags,
            "audio_file": f"/audio/{os.path.basename(audio_file)}"
        }
        notes.append(note_entry)
        save_notes(notes)
        return render_template("index2.html", notes=notes, success="Note saved successfully!")

    return render_template("index.html", notes=notes)


@app.route("/audio/<filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)


@app.route("/search")
def search():
    query = request.args.get("q", "").lower()
    notes = load_notes()
    results = [n for n in notes if query in n["text"].lower() or
               (n.get("summary") and query in n["summary"].lower()) or
               query in " ".join(n["tags"]).lower()]
    return jsonify(results)


if __name__ == "__main__":
    app.run(debug=False)
