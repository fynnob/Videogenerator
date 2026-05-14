import os
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

def upload_video():
    creds_raw = os.environ.get("YOUTUBE_CREDENTIALS")
    if not creds_raw:
        raise ValueError("Missing YOUTUBE_CREDENTIALS secret!")

    if not os.path.exists("post.json"):
        raise FileNotFoundError("post.json not found!")

    with open("post.json", "r") as f:
        post_data = json.load(f)

    raw_title   = post_data.get("title", "Reddit Story")
    subreddit   = post_data.get("subreddit", "reddit")
    video_title = raw_title[:100]  # YouTube 100 char limit, no #shorts tag

    creds_info = json.loads(creds_raw)
    creds      = Credentials.from_authorized_user_info(creds_info)
    youtube    = build("youtube", "v3", credentials=creds)

    print(f"Uploading: {video_title}")

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": video_title,
                "description": (
                    f"Story from r/{subreddit}\n\n"
                    f"#reddit #redditstories #{subreddit}"
                ),
                "categoryId": "24",  # Entertainment
                "tags": [
                    "reddit", "reddit stories", "reddit story",
                    "stories", subreddit,
                ]
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        },
        media_body=MediaFileUpload("output.mp4", chunksize=-1, resumable=True)
    )

    response = request.execute()
    print(f"Video live! ID: {response.get('id')}")

if __name__ == "__main__":
    upload_video()
