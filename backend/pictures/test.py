from insightface.app import FaceAnalysis
import numpy as np, cv2

face_app = FaceAnalysis(name="buffalo_l")
face_app.prepare(ctx_id=0, det_size=(640,640))

img1 = cv2.imread("./69d50731.jpg")
img2 = cv2.imread("./parker.jpg")

face1 = face_app.get(img1)[0]
face2 = face_app.get(img2)[0]

# AI-based comparison
sim = np.dot(face1.embedding, face2.embedding) / (
    np.linalg.norm(face1.embedding) * np.linalg.norm(face2.embedding)
)
print("Similarity:", sim)
if sim > 0.35:  # model’s own verified threshold
    print("✅ Same person")
else:
    print("❌ Different person")