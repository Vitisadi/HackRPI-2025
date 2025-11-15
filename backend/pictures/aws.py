import boto3
import json

# === AWS Keys (only for local/hackathon use) ===
AWS_ACCESS_KEY = ""
AWS_SECRET_KEY = ""
REGION = ""  # or your AWS region

# === Initialize Rekognition client ===
rekog = boto3.client(
    "rekognition",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=REGION
)

# === Function: Compare two faces ===
def compare_faces(source_path, target_path, threshold=80):
    """Compares two local images and returns similarity score."""
    with open(source_path, "rb") as src, open(target_path, "rb") as tgt:
        response = rekog.compare_faces(
            SourceImage={"Bytes": src.read()},
            TargetImage={"Bytes": tgt.read()},
            SimilarityThreshold=threshold
        )

    # Print results
    if response["FaceMatches"]:
        match = response["FaceMatches"][0]
        print(f"✅ Faces match with {match['Similarity']:.2f}% similarity.")
        return match["Similarity"]
    else:
        print("❌ No match found.")
        return 0

# === Test ===
if __name__ == "__main__":
    sim = compare_faces("./shimu_mystery.jpg", "./shimu.jpg")
    print("Similarity score:", sim)