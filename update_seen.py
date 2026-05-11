import json
import os
from datetime import datetime

SEEN_FILE = "seen_posts.json"

def update_seen():
    # Load post that was just processed
    with open("post.json", "r") as f:
        post = json.load(f)

    # Load existing seen data
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            seen_data = json.load(f)
    else:
        seen_data = {"seen_ids": [], "videos": []}

    # Add this post
    seen_data["seen_ids"].append(post["id"])
    seen_data["videos"].append({
        "post_id":   post["id"],
        "title":     post["title"],
        "subreddit": post["subreddit"],
        "voice":     post["voice"],
        "score":     post["score"],
        "made_at":   datetime.utcnow().isoformat()
    })

    with open(SEEN_FILE, "w") as f:
        json.dump(seen_data, f, indent=2)

    print(f"✅ Marked post {post['id']} as seen. Total seen: {len(seen_data['seen_ids'])}")

if __name__ == "__main__":
    update_seen()
