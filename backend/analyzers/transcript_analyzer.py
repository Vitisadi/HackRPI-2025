import os
import time
import json
import whisper
from dotenv import load_dotenv
from google import genai

# === Gemini setup ===
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# === 🧠 Preload Whisper model once globally ===
print("🔊 Loading Whisper model (small)...")
whisper_model = whisper.load_model("small")  # preload once

def analyze_transcript(video_path: str):
    """
    Transcribe the input video and analyze the conversation using Gemini.
    Returns a structured dict with guessed name and dialogue.
    """
    print(f"🎙️ Transcribing {video_path} ...")

    curr_time = time.time()

    # === Step 1: Transcribe audio ===
    try:
        result = whisper_model.transcribe(video_path, language="English", fp16=False)
    except Exception as e:
        print(f"❌ Whisper error: {e}")
        return {"guessed_name": None, "conversation": [], "raw_text": "", "error": str(e)}

    transcript_text = "\n".join(
        [f"[{seg['start']:.2f}s–{seg['end']:.2f}s]: {seg['text']}" for seg in result["segments"]]
    )

    print(f"✅ Transcription complete in {time.time() - curr_time:.2f} seconds.")

    # === Step 2: Create Gemini prompt ===
    prompt = f"""
    You are an intelligent assistant analyzing a transcript of a short two-person conversation.

    Context:
    - The person speaking in the video starts the conversation.
    - The first personal name that appears immediately after any greeting word 
    (such as "hi", "hey", "hello", "good morning", "good afternoon", "what’s up", "yo", etc.)
    belongs to the **other person** being spoken to.
    - That detected name remains the other person’s name throughout the conversation — 
    even if the speaker’s own name is mentioned later (for example, "Hi Jimmy" → guessed_name = Jimmy, 
    even if "Nicko" appears later).

    Your tasks:
    1. Detect the first human name that follows a greeting word — that is the other person's name.
    2. Use "Me" for the speaker in the video, and the detected name for the other person.
    3. Output valid JSON **only**, following this exact structure:

    {{
    "guessed_name": "<detected name or 'Other Person'>",
    "conversation": [
        {{
        "speaker": "Me" or "<guessed_name>",
        "text": "<exact line from transcript>"
        }}
    ]
    }}

    Rules:
    - Output must be valid JSON (no markdown, comments, or text outside the JSON).
    - Keep each spoken line exactly as it appears.
    - Use only the first detected name after a greeting.
    - Ignore all other names mentioned later.
    - If no name is detected, set guessed_name = "Other Person".

    Transcript:
    {transcript_text}
    """

    # === Step 3: Call Gemini ===
    try:
        response = client.models.generate_content(model="gemini-2.0-flash-lite", contents=prompt)
        text_output = response.text.strip()
        print(f"✅ Gemini response received in {time.time() - curr_time:.2f} seconds.")
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        return {"guessed_name": None, "conversation": [], "raw_text": transcript_text, "error": str(e)}

    # === Step 4: Validate Gemini response ===
    try:
        if text_output.startswith("```"):
            text_output = text_output.strip("`").replace("json", "").strip()
        data = json.loads(text_output)
        print(f"✅ Transcript analysis complete. Guessed name: {data.get('guessed_name')}")
        return {
            "guessed_name": data.get("guessed_name"),
            "conversation": data.get("conversation", []),
            "raw_text": transcript_text
        }
    except json.JSONDecodeError:
        print("⚠️ Gemini output was not valid JSON, returning fallback.")
        return {
            "guessed_name": None,
            "conversation": [],
            "raw_text": transcript_text,
            "gemini_raw": text_output
        }