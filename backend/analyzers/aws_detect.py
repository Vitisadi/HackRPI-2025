import boto3
import os
from dotenv import load_dotenv

load_dotenv()
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
REGION = os.getenv("AWS_REGION", "us-east-1")

# === Initialize Rekognition client ===
rekog = boto3.client(
    "rekognition",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=REGION
)

# === Use this function in place of ai_face_similarity ===
def aws_face_similarity(img1_path, img2_path):
    """Compare two local images using AWS Rekognition."""
    with open(img1_path, "rb") as img1, open(img2_path, "rb") as img2:
        response = rekog.compare_faces(
            SourceImage={"Bytes": img1.read()},
            TargetImage={"Bytes": img2.read()},
            SimilarityThreshold=0  # we’ll handle threshold manually
        )

    if response["FaceMatches"]:
        return response["FaceMatches"][0]["Similarity"]
    else:
        return 0.0