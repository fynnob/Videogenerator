import requests
import json
import os
import sys
import re
import random
from datetime import datetime

# --- Config ---
SUBREDDITS = [
    "AmItheAsshole",
    "tifu",
    "TrueOffMyChest",
    "confession",
    "offmychest",
    "relationship_advice",
]
MIN_UPVOTES = 1000
MIN_WORDS   = 150
MAX_WORDS   = 800
SEEN_FILE   = "seen_posts.json"

HEADERS = {
    # Reddit requires a descriptive User-Agent or it rate-limits/blocks you
    "User-Agent": "RedditVideoBot/1.0 (automated video creation; one request per hour)"
}

# ---------------------------------------------------------------------------
# Text cleanup — expand Reddit shorthand so TTS sounds natural
# ---------------------------------------------------------------------------

# Order matters: longer/more specific patterns first
REPLACEMENTS = [
    # Reddit post-specific slang
    (r"\bAITA\b",           "Am I the asshole"),
    (r"\baita\b",           "am I the asshole"),
    (r"\bWIBTA\b",          "would I be the asshole"),
    (r"\bwibta\b",          "would I be the asshole"),
    (r"\bNTA\b",            "not the asshole"),
    (r"\bnta\b",            "not the asshole"),
    (r"\bYTA\b",            "you're the asshole"),
    (r"\byta\b",            "you're the asshole"),
    (r"\bESH\b",            "everyone sucks here"),
    (r"\besh\b",            "everyone sucks here"),
    (r"\bNAH\b",            "no assholes here"),
    (r"\bnah\b",            "no assholes here"),
    (r"\bINFO\b",           "I need more information"),
    (r"\bTIFU\b",           "today I messed up"),
    (r"\btifu\b",           "today I messed up"),
    (r"\bOP\b",             "the original poster"),
    (r"\bop\b",             "the original poster"),

    # Common internet abbreviations
    (r"\bIMO\b",            "in my opinion"),
    (r"\bimo\b",            "in my opinion"),
    (r"\bIMHO\b",           "in my honest opinion"),
    (r"\bimho\b",           "in my honest opinion"),
    (r"\bIIRC\b",           "if I recall correctly"),
    (r"\biirc\b",           "if I recall correctly"),
    (r"\bIDK\b",            "I don't know"),
    (r"\bidk\b",            "I don't know"),
    (r"\bIDC\b",            "I don't care"),
    (r"\bidc\b",            "I don't care"),
    (r"\bTBH\b",            "to be honest"),
    (r"\btbh\b",            "to be honest"),
    (r"\bTBF\b",            "to be fair"),
    (r"\btbf\b",            "to be fair"),
    (r"\bNGL\b",            "not gonna lie"),
    (r"\bngl\b",            "not gonna lie"),
    (r"\bOMG\b",            "oh my god"),
    (r"\bomg\b",            "oh my god"),
    (r"\bWTF\b",            "what the heck"),
    (r"\bwtf\b",            "what the heck"),
    (r"\bBF\b",             "boyfriend"),
    (r"\bGF\b",             "girlfriend"),
    (r"\bDH\b",             "dear husband"),
    (r"\bDW\b",             "dear wife"),
    (r"\bMIL\b",            "mother in law"),
    (r"\bFIL\b",            "father in law"),
    (r"\bSIL\b",            "sister in law"),
    (r"\bBIL\b",            "brother in law"),
    (r"\bSO\b",             "significant other"),
    (r"\bLDR\b",            "long distance relationship"),
    (r"\bDM\b",             "direct message"),
    (r"\bIRL\b",            "in real life"),
    (r"\birl\b",            "in real life"),
    (r"\bFYI\b",            "for your information"),
    (r"\bfyi\b",            "for your information"),
    (r"\bJK\b",             "just kidding"),
    (r"\bjk\b",             "just kidding"),
    (r"\bLOL\b",            "laughing out loud"),
    (r"\blol\b",            "laughing out loud"),
    (r"\bLMAO\b",           "laughing out loud"),
    (r"\blmao\b",           "laughing out loud"),
    (r"\bSMH\b",            "shaking my head"),
    (r"\bsmh\b",            "shaking my head"),
    (r"\bFML\b",            "this is my life"),
    (r"\bfml\b",            "this is my life"),
    (r"\bTL;DR\b",          "to summarize"),
    (r"\btl;dr\b",          "to summarize"),
    (r"\bTLDR\b",           "to summarize"),
    (r"\btldr\b",           "to summarize"),

    # Formatting artifacts that sound bad in TTS
    (r"\*\*(.+?)\*\*",      r"\1"),   # bold markdown
    (r"\*(.+?)\*",          r"\1"),   # italic markdown
    (r"\_(.+?)\_",          r"\1"),   # underscore italic
    (r"~~(.+?)~~",          r"\1"),   # strikethrough
    (r"`(.+?)`",            r"\1"),   # inline code
    (r"&amp;",              "and"),
    (r"&lt;",               "less than"),
    (r"&gt;",               "greater than"),
    (r"&nbsp;",             " "),

    # Clean up excessive newlines / whitespace
    (r"\n{3,}",             "\n\n"),
    (r"[ \t]{2,}",          " "),
]

def clean_text(text):
    for pattern, replacement in REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    return text.strip()

# ---------------------------------------------------------------------------
# Gender detection for voice selection
# ---------------------------------------------------------------------------

def detect_gender(text):
    text_lower = text.lower()
    female_signals = ["my husband", "my boyfriend", "my brother", "my dad",
                      "my father", "my son", "my male", "my boy"]
    male_signals   = ["my wife", "my girlfriend", "my sister", "my mom",
                      "my mother", "my daughter", "my female", "my girl"]
    female_score = sum(1 for s in female_signals if s in text_lower)
    male_score   = sum(1 for s in male_signals   if s in text_lower)
    if female_score > male_score:
        return "female"
    elif male_score > female_score:
        return "male"
    return None

def pick_voice(text):
    gender = detect_gender(text)
    if gender == "female":
        return "en-US-JennyNeural"
    elif gender == "male":
        return "en-US-GuyNeural"
    return random.choice(["en-US-GuyNeural", "en-US-JennyNeural"])

# ---------------------------------------------------------------------------
# Seen posts state
# ---------------------------------------------------------------------------

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    return {"seen_ids": [], "videos": []}

# ---------------------------------------------------------------------------
# Reddit JSON fetching (no API key needed)
# ---------------------------------------------------------------------------

def fetch_subreddit(subreddit, limit=50):
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()["data"]["children"]

def fetch_best_post():
    seen_data = load_seen()
    seen_ids  = set(seen_data["seen_ids"])

    for subreddit in SUBREDDITS:
        print(f"Checking r/{subreddit}...")
        try:
            posts = fetch_subreddit(subreddit)
        except Exception as e:
            print(f"   Failed to fetch r/{subreddit}: {e}")
            continue

        for item in posts:
            post = item["data"]

            if post["id"] in seen_ids:
                continue
            if post.get("score", 0) < MIN_UPVOTES:
                continue
            if not post.get("is_self", False):
                continue

            raw_text = post.get("selftext", "")
            if not raw_text or raw_text in ("[removed]", "[deleted]"):
                continue

            word_count = len(raw_text.split())
            if word_count < MIN_WORDS or word_count > MAX_WORDS:
                continue

            clean_title = clean_text(post["title"])
            clean_body  = clean_text(raw_text)
            voice       = pick_voice(clean_body)

            result = {
                "id":          post["id"],
                "title":       clean_title,
                "text":        clean_body,
                "raw_title":   post["title"],
                "subreddit":   subreddit,
                "score":       post["score"],
                "voice":       voice,
                "word_count":  word_count,
                "fetched_at":  datetime.utcnow().isoformat(),
            }

            with open("post.json", "w") as f:
                json.dump(result, f, indent=2)

            print(f"Found: {clean_title[:60]}...")
            print(f"   r/{subreddit} | Score: {post['score']} | Words: {word_count} | Voice: {voice}")
            return result

    print("No suitable posts found this run.")
    sys.exit(1)

if __name__ == "__main__":
    fetch_best_post()
