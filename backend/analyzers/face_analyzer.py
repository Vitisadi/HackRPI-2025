import time
import cv2, json, uuid
from pathlib import Path
import numpy as np
import face_recognition
from insightface.app import FaceAnalysis
from .aws_detect import aws_face_similarity

# === Load InsightFace model ===
print("🔍 Loading InsightFace model (buffalo_l)...")
face_app = FaceAnalysis(name="buffalo_l")
face_app.prepare(ctx_id=0, det_size=(640,640))  # higher res for better detection

# === CONFIG ===
DB_ROOT = Path(__file__).resolve().parents[1] / "faces_db"
FACES_DIR = DB_ROOT / "faces"
TEMP_DIR = DB_ROOT / "temp_crops"

FACE_MATCH_THRESHOLD = 0.25   # higher = more lenient
FRAME_INTERVAL_SEC = 2      # analyze every ~1.5 seconds
MIN_VALID_FRAMES = 3          # minimum clear frames to proceed

# === Setup folders ===
FACES_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# === Save cropped face with margin ===
def save_temp_crop(frame, top, right, bottom, left, margin=0.5):
    """Crop a face with margin (to include some background)."""
    h, w, _ = frame.shape
    face_h, face_w = bottom - top, right - left
    pad_y, pad_x = int(face_h * margin), int(face_w * margin)

    top = max(0, top - pad_y)
    bottom = min(h, bottom + pad_y)
    left = max(0, left - pad_x)
    right = min(w, right + pad_x)

    crop = frame[top:bottom, left:right]
    crop = cv2.convertScaleAbs(crop, alpha=1.5, beta=40)  # brighten
    crop = cv2.bilateralFilter(crop, 5, 75, 75)           # smooth noise

    filename = f"{uuid.uuid4().hex[:8]}.jpg"
    path = TEMP_DIR / filename
    cv2.imwrite(str(path), crop)
    return str(path)

# === Compare with all saved faces ===
def compare_with_all_faces(new_face_path):
    """Compare the new cropped face against all faces in faces_db/faces."""
    best_match = None
    best_score = -1.0

    for face_file in FACES_DIR.glob("*.*"):
        if not face_file.is_file():
            continue
        try:
            print(f"🧠 Comparing new: {new_face_path}  ↔️  existing: {face_file}")
            sim = aws_face_similarity(new_face_path, face_file)  # 🔹 using AWS
            print(f"🔍 {face_file.stem}: similarity={sim:.3f}")
            if sim > best_score:
                best_score = sim
                best_match = face_file.stem
        except Exception as e:
            print(f"⚠️ Skipping {face_file.name}: {e}")

    if best_score >= 80:  # AWS similarity is 0–100 scale
        print(f"✅ Best match: {best_match} (similarity={best_score:.2f}%)")
        return {"status": "old", "name": best_match, "similarity": best_score}
    else:
        print("🆕 No matching face found.")
        return {"status": "new", "similarity": best_score, "face_path": new_face_path}


# === Main video analyzer ===
def analyze_video(video_path: str):
    """Find the clearest and most centered face from the video."""
    start_time = time.time()
    print(f"🎥 Analyzing faces in: {video_path}")
    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        return {"status": "error", "message": "Cannot open video file."}

    fps = int(video.get(cv2.CAP_PROP_FPS)) or 25
    frame_step = max(int(fps * FRAME_INTERVAL_SEC), 1)
    frame_count = 0
    best_crop = None
    best_score = 0
    valid_frames = 0

    while True:
        ret, frame = video.read()
        if not ret:
            break
        if frame_count % frame_step == 0:
            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locs = face_recognition.face_locations(rgb, model="hog")
            if not locs:
                frame_count += 1
                continue

            valid_frames += 1
            for (top, right, bottom, left) in locs:
                # --- area score (bigger = closer) ---
                area = (right - left) * (bottom - top)
                area_score = area / (w * h)

                # --- center score (face near center = better) ---
                face_cx = (left + right) / 2
                face_cy = (top + bottom) / 2
                frame_cx = w / 2
                frame_cy = h / 2
                dist = np.sqrt((face_cx - frame_cx)**2 + (face_cy - frame_cy)**2)
                max_dist = np.sqrt((w/2)**2 + (h/2)**2)
                center_score = 1 - (dist / max_dist)

                # --- total score (weighted) ---
                score = (area_score * 0.7) + (center_score * 0.3)

                if score > best_score:
                    best_score = score
                    best_crop = save_temp_crop(frame, top, right, bottom, left)

        frame_count += 1

    video.release()

    if valid_frames < MIN_VALID_FRAMES or not best_crop:
        print("⚠️ Too few valid frames or unclear face.")
        return {"status": "no_face"}

    elapsed = time.time() - start_time
    print(f"✅ analyze_video completed in {elapsed:.2f} seconds.")
    print(f"🧠 Best cropped face saved: {best_crop} (score={best_score:.3f})")
    return compare_with_all_faces(best_crop)

# === Example Run ===
if __name__ == "__main__":
    result = analyze_video("../videos/nikul.mp4")
    print(json.dumps(result, indent=2))