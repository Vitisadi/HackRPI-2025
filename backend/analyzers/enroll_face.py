# enroll_face.py  — simplified “flat” version
import cv2, face_recognition, numpy as np, json
from pathlib import Path

# === CONFIG ===
DB_ROOT = Path("faces_db")
FACE_DIR = DB_ROOT / "faces"
EMBED_PATH = DB_ROOT / "embeddings.json"

FACE_DIR.mkdir(parents=True, exist_ok=True)
if not EMBED_PATH.exists():
    EMBED_PATH.write_text("{}", encoding="utf-8")


# === Utility functions ===
def load_db():
    return json.loads(EMBED_PATH.read_text(encoding="utf-8"))

def save_db(db):
    EMBED_PATH.write_text(json.dumps(db, indent=2), encoding="utf-8")


# === Core enrollment ===
def enroll(image_path: str, name: str):
    """
    Register a new face embedding and image.
    Saves:
      faces_db/faces/{name}.jpg
      faces_db/embeddings.json  → { name: {embedding, image_path} }
    """
    if not Path(image_path).exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    bgr = cv2.imread(image_path)
    if bgr is None:
        raise ValueError(f"Could not load image: {image_path}")

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    locs = face_recognition.face_locations(rgb, model="hog")

    if not locs:
        raise ValueError("No face detected in the image.")

    # Use the first face
    enc = face_recognition.face_encodings(rgb, locs)[0]
    # Save cropped face
    safe_name = name.lower().replace(" ", "_")
    save_path = FACE_DIR / f"{safe_name}.jpg"
    cv2.imwrite(str(save_path), bgr)

    # Update embeddings database
    db = load_db()
    db[name] = str(save_path)
    save_db(db)

    print(f"✅ Enrolled {name} → {save_path}")
    return {"name": name, "image_path": str(save_path)}


# === Optional test entry point ===
if __name__ == "__main__":
    # quick test (replace with your own image)
    test_img = "faces_db/temp_crops/unknown_face.jpg"
    enroll(test_img, "Tim")