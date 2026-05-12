import os
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

def upload():
    # Load credentials from GitHub Secret
    creds_json = os.environ["YOUTUBE_CREDENTIALS"]
    creds_data = json.loads(creds_json)
    creds = Credentials.from_authorized_user_info(creds_data)

    youtube = build("youtube", "v3", credentials=creds)

    with open("post.json", "r") as f:
        post = json.load(f)

    request_body = {
        "snippet": {
            "title": post["title"][:100],
            "description": f"Best of r/{post['subreddit']} #shorts #reddit #story",
            "categoryId": "24", # Entertainment
            "tags": ["reddit", "shorts", post["subreddit"]]
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }

    media = MediaFileUpload("output.mp4", chunksize=-1, resumable=True)
    
    print("Uploading to YouTube...")
    response = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    ).execute()

    print(f"✅ Video uploaded! ID: {response['id']}")

if __name__ == "__main__":
    upload()
