import os
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

def upload_video():
    # 1. Grab the secret from GitHub
    creds_raw = os.environ.get("YOUTUBE_CREDENTIALS")
    if not creds_raw:
        raise ValueError("Missing YOUTUBE_CREDENTIALS secret!")

    # 2. Reconstruct the credentials
    creds_info = json.loads(creds_raw)
    creds = Credentials.from_authorized_user_info(creds_info)

    # 3. Build the YouTube service
    youtube = build("youtube", "v3", credentials=creds)

    # 4. Define the video
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": "Reddit Story #shorts",
                "description": "Auto-generated content",
                "categoryId": "24" # Entertainment
            },
            "status": {"privacyStatus": "public"}
        },
        media_body=MediaFileUpload("output.mp4")
    )
    request.execute()
    print("🚀 Video is live!")

if __name__ == "__main__":
    upload_video()
