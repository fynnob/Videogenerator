import os
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

def upload_video():
    # 1. Grab the secret from GitHub
    creds_raw = os.environ.get("YOUTUBE_CREDENTIALS")
    if not creds_raw:
        raise ValueError("❌ Missing YOUTUBE_CREDENTIALS secret!")

    # 2. Load the Reddit post data to get the title
    if not os.path.exists("post.json"):
        raise FileNotFoundError("❌ post.json not found! Can't determine video title.")
    
    with open("post.json", "r") as f:
        post_data = json.load(f)
    
    # 🔧 FIX: Set the title dynamically. 
    # YouTube has a 100-character limit, so we trim it to 85 to leave room for the hashtag.
    raw_title = post_data.get("title", "Reddit Story")
    video_title = f"{raw_title[:85]} #shorts"

    # 3. Reconstruct the credentials
    creds_info = json.loads(creds_raw)
    creds = Credentials.from_authorized_user_info(creds_info)

    # 4. Build the YouTube service
    youtube = build("youtube", "v3", credentials=creds)

    # 5. Define and execute the upload
    print(f"🚀 Uploading video with title: {video_title}")
    
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": video_title,
                "description": f"Story from r/{post_data.get('subreddit', 'reddit')}\n\n#shorts #reddit #story",
                "categoryId": "24", # Entertainment
                "tags": ["reddit", "story", "shorts", "#short", "#redditetory","#stories", "#shortstories", post_data.get('subreddit')]
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False
            }
        },
        media_body=MediaFileUpload("output.mp4", chunksize=-1, resumable=True)
    )
    
    response = request.execute()
    print(f"✅ Video is live! ID: {response.get('id')}")

if __name__ == "__main__":
    upload_video()
