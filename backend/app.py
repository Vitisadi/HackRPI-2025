# app.py
import os
import json
import threading
import time
from pathlib import Path
from analyzers.face_analyzer import analyze_video
from analyzers.transcript_analyzer import analyze_transcript
from analyzers.enroll_face import enroll
from analyzers.transcript_analyzer import whisper_model
from analyzers.face_analyzer import face_app

print("✅ All AI models preloaded (Whisper + InsightFace). Ready to process requests.")

# 🔹 NEW IMPORTS
from flask import Flask, jsonify, send_from_directory, request

# === PATH SETUP ===
BASE_DIR = Path(__file__).resolve().parent
MEMORY_DIR = BASE_DIR / "conversations"
DB_ROOT = BASE_DIR / "faces_db"
FACES_DIR = DB_ROOT / "faces"
TEMP_DIR = DB_ROOT / "temp_crops"

# ✅ Ensure all folders exist
for d in [MEMORY_DIR, DB_ROOT, FACES_DIR, TEMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 🔹 Initialize Flask
app = Flask(__name__)

# === API ROUTES ===
# returns people name and image URLs
"""
req: http://localhost:3000/api/people - GET
returns:
[
    {
        "image_url": "http://localhost:3000/faces/tim.jpg",
        "name": "tim"
    },
    {
        "image_url": "http://localhost:3000/faces/parker.jpg",
        "name": "parker"
    },
    {
        "image_url": "http://localhost:3000/faces/nicko.jpg",
        "name": "nicko"
    }
]
"""
@app.route("/api/people", methods=["GET"])
def get_people():
    """Return all recognized people and their images."""
    people = []
    for face_file in FACES_DIR.glob("*.*"):
        if face_file.is_file():
            people.append({
                "name": face_file.stem,
                "image_url": f"http://localhost:3000/faces/{face_file.name}"
            })
    return jsonify(people)

# return face images
"""
req: http://localhost:3000/faces/tim.jpg - GET
returns: image file
""" 
@app.route("/faces/<filename>")
def serve_face(filename):
    """Serve face images."""
    return send_from_directory(str(FACES_DIR), filename)

# return conversation history for a person
"""
req: http://localhost:3000/api/conversation/tim - GET
returns: conversation JSON
"""
@app.route("/api/conversation/<name>", methods=["GET"])
def get_conversation(name):
    """Return conversation history for a given person."""
    conv_path = MEMORY_DIR / f"{name}.json"
    if not conv_path.exists():
        return jsonify({
            "name": name,
            "conversation": [],
            "message": "No conversation found for this person."
        }), 404
    try:
        with open(conv_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"name": name, "conversation": data})

# process uploaded video
"""
req: http://localhost:3000/api/process - POST
form-data: file: <video file>
returns: processing result JSON
"""
@app.route("/api/process", methods=["POST"])
def process_upload():
    """Upload a video, process it (face + transcript), and return results."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    curr_time = time.time()
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    uploads_dir = BASE_DIR / "uploads"
    uploads_dir.mkdir(exist_ok=True)
    video_path = uploads_dir / file.filename
    file.save(video_path)

    print(f"📁 Uploaded video saved to: {video_path}")

    try:
        result = process_video(str(video_path))
    except Exception as e:
        print("❌ Error while processing:", e)
        return jsonify({"error": str(e)}), 500

    print(f"🚀 TOTAL VIDEO PROCESSING: {time.time() - curr_time:.2f} seconds.")
    return jsonify(result)

# === GLOBAL THREAD VARS ===
transcript_result = {}
transcript_done = threading.Event()

def run_transcript(video_path):
    """Thread: run Whisper + Gemini transcript analyzer"""
    global transcript_result
    transcript_result = analyze_transcript(video_path)
    transcript_done.set()

def run_face(video_path):
    """Thread: detect face, wait for transcript if new person"""
    face_result = analyze_video(video_path)

    # 🧠 If new face detected, wait for transcript to identify the name
    if face_result["status"] == "new":
        print("🕒 New face detected — waiting for transcript to identify name...")
        transcript_done.wait(timeout=180)  # wait up to 3 minutes for Gemini
        time.sleep(0.10) 

        # 🧩 After transcript finishes, get the detected name
        name = transcript_result.get("guessed_name", "Unknown")
        face_result["name"] = name

        # 🧠 Enroll only after transcript gives a valid name
        face_path = face_result.get("face_path")
        if name and name.lower() != "unknown" and face_path:
            try:
                enroll(face_path, name)
                face_result["auto_enrolled"] = True
                print(f"✅ Auto-enrolled new person as: {name}")
            except Exception as e:
                print(f"⚠️ Enrollment failed for {name}: {e}")
                face_result["auto_enrolled"] = False
        else:
            print("⚠️ Could not auto-enroll — missing name or face path.")
            face_result["auto_enrolled"] = False

    else:
        # 🧠 If existing face matched, no need to wait for transcript
        face_result["auto_enrolled"] = False

    # Merge conversation for return consistency
    face_result["conversation"] = transcript_result.get("conversation", [])
    return face_result

def process_video(video_path):
    print(f"\n🚀 Processing video: {video_path}\n")

    global transcript_result
    transcript_result = {}      # 🔹 clear any old transcript data
    transcript_done.clear()

    face_result_box = {}
    t1 = threading.Thread(target=run_transcript, args=(video_path,))

    def face_thread_wrapper():
        face_result_box["data"] = run_face(video_path)

    t2 = threading.Thread(target=face_thread_wrapper)

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    face_result = face_result_box.get("data", {"status": "unknown"})

    final = {
        "video_path": video_path,
        "guessed_name": transcript_result.get("guessed_name"),
        "conversation": transcript_result.get("conversation", []),
        "face_status": face_result.get("status", "unknown"),
        "face_name": face_result.get("name"),
        "auto_enrolled": face_result.get("auto_enrolled", False),
    }

    save_conversation(final)
    print("\n=== FINAL RESULT ===")
    print(json.dumps(final, indent=2))
    return final

def save_conversation(data):
    """Append conversation JSON for each person."""
    name = data.get("face_name") or data.get("guessed_name") or "Unknown"
    path = MEMORY_DIR / f"{name}.json"

    existing = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            print(f"⚠️ Could not parse old file for {name}, resetting it.")

    entry = {"timestamp": int(time.time()), "conversation": data.get("conversation", [])}
    existing.append(entry)
    path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    print(f"💾 Conversation history updated for: {name}")

# === START FLASK APP ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)