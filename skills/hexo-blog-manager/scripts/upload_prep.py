import base64
import json
import os
import sys

def upload_to_oss(image_path, repo_path, message):
    """
    准备上传到 GitHub OSS 的 JSON 负载文件
    """
    if not os.path.exists(image_path):
        print(f"Error: File {image_path} not found.")
        sys.exit(1)

    with open(image_path, 'rb') as f:
        content = base64.b64encode(f.read()).decode()

    payload = {
        "message": message,
        "content": content,
        "branch": "main"
    }

    output_payload = 'temp_payload.json'
    with open(output_payload, 'w') as f:
        json.dump(payload, f)

    print(f"Payload created at {output_payload}. Ready for 'gh api' upload.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python upload_prep.py <image_path> <commit_message>")
        sys.exit(1)
    
    upload_to_oss(sys.argv[1], "", sys.argv[2])
