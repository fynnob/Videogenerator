import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import html
import json
import os
import sys
import re
import random
from datetime import datetime

# --- Config ---
# I added a few more story-heavy subreddits to give you more variety
SUBREDDITS = [
    "AmItheAsshole",
    "tifu",
    "TrueOffMyChest",
    "confession",
    "offmychest",
    "relationship_advice",
    "stories",
    "LifeProTips",
    "AskReddit" 
]

MIN_WORDS   = 150
MAX_WORDS   = 400
SEEN_FILE   = "seen_posts.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ---------------------------------------------------------------------------
# Text cleanup — expanding shorthand so the AI voice sounds natural
# ---------------------------------------------------------------------------
REPLACEMENTS = [
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
    (r"\bAFK\b",            "away from keyboard"),
    (r"\bJK\b",             "just kidding"),
    (r"\bjk\b",             "just kidding"),
    (r"\bLOL\b",            "laughing out loud"),
    (r"\blol\b",            "laughing out loud"),
    (r"\bLMAO\b",           "laughing my ass off"),
    (r"\blmao\b",           "laughing out loud"),
    (r"\bROFL\b",           "rolling on the floor laughing"),
    (r"\bSMH\b",            "shaking my head"),
    (r"\bsmh\b",            "shaking my head"),
    (r"\bFML\b",            "this is my life"),
    (r"\bfml\b",            "this is my life"),
    (r"\bTL;DR\b",          "to summarize"),
    (r"\btl;dr\b",          "to summarize"),
    (r"\bTLDR\b",           "to summarize"),
    (r"\btldr\b",           "to summarize"),
    (r"\*\*(.+?)\*\*",      r"\1"),   
    (r"\*(.+?)\*",          r"\1"),   
    (r"\_(.+?)\_",          r"\1"),   
    (r"~~(.+?)~~",          r"\1"),   
    (r"`(.+?)`",            r"\1"),   
    (r"&amp;",              "and"),
    (r"&lt;",               "less than"),
    (r"&gt;",               "greater than"),
    (r"&nbsp;",             " "),
    (r"\n{3,}",             "\n\n"),
    (r"[ \t]{2,}",          " "),
]

def clean_text(text):
    for pattern, replacement in REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    return text.strip()

def detect_gender(text):
    text_lower = text.lower()
    female_signals = ["my husband", "my boyfriend", "my brother", "my dad", "my father", "my son", "my male", "my boy"]
    male_signals   = ["my wife", "my girlfriend", "my sister", "my mom", "my mother", "my daughter", "my female", "my girl"]
    f_score = sum(1 for s in female_signals if s in text_lower)
    m_score = sum(1 for s in male_signals if s in text_lower)
    return "female" if f_score > m_score else "male" if m_score > f_score else None

def pick_voice(text):
    gender = detect_gender(text)
    return "en-US-JennyNeural" if gender == "female" else "en-US-GuyNeural" if gender == "male" else random.choice(["en-US-GuyNeural", "en-US-JennyNeural"])

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    return {"seen_ids": [], "videos": []}

def fetch_subreddit_rss(subreddit):
    url = f"https://www.reddit.com/r/{subreddit}/hot.rss?limit=50"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as response:
        return ET.fromstring(response.read())

def fetch_best_post():
    seen_data = load_seen()
    seen_ids  = set(seen_data["seen_ids"])
    ns = {'atom': 'http://www.w3.org/2005/Atom'}

    # 🔧 RANDOMIZER: Shuffle the list so we check subreddits in a random order
    random_subs = SUBREDDITS.copy()
    random.shuffle(random_subs)

    for subreddit in random_subs:
        print(f"🔍 Checking r/{subreddit}...")
        try:
            root = fetch_subreddit_rss(subreddit)
        except Exception as e:
            print(f"   ⚠️  Failed to fetch: {e}")
            continue

        for entry in root.findall('atom:entry', ns):
            link_node = entry.find('atom:link', ns)
            post_link = link_node.attrib.get('href', '') if link_node is not None else ""
            post_id_match = re.search(r'/comments/([^/]+)/', post_link)
            post_id = post_id_match.group(1) if post_id_match else post_link
            
            if post_id in seen_ids or not post_id:
                continue

            title_node = entry.find('atom:title', ns)
            raw_title = title_node.text if title_node is not None else ""
            content_node = entry.find('atom:content', ns)
            if content_node is None: continue
                
            # RSS Cleanup logic
            raw_text = html.unescape(content_node.text or "")
            raw_text = re.sub(r'<[^>]+>', ' ', raw_text)
            raw_text = re.sub(r'submitted by\s*/u/[\w-]+\s*', '', raw_text, flags=re.IGNORECASE)
            raw_text = raw_text.replace('[link]', '').replace('[comments]', '').strip()

            word_count = len(raw_text.split())
            if word_count < MIN_WORDS or word_count > MAX_WORDS:
                continue

            # 🔧 CONVERSION: Clean and expand shorthand
            clean_title = clean_text(raw_title)
            clean_body  = clean_text(raw_text)
            voice       = pick_voice(clean_body)

            result = {
                "id":          post_id,
                "title":       clean_title,
                "text":        clean_body,
                "subreddit":   subreddit,
                "voice":       voice,
                "word_count":  word_count,
                "fetched_at":  datetime.utcnow().isoformat(),
            }

            with open("post.json", "w") as f:
                json.dump(result, f, indent=2)

            print(f"✅ Found Post: {clean_title[:50]}... in r/{subreddit}")
            return result

    print("❌ No new posts found.")
    sys.exit(1)

if __name__ == "__main__":
    fetch_best_post()
