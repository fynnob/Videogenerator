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
SUBREDDITS = [
    "BestofRedditorUpdates", # The one you just showed me! (Excellent for long form)
    "ProRevenge",             # High word counts, usually 1000+
    "MaliciousCompliance",    # Very detailed stories
    "entitledparents",        # Long dialogues
    "MilitaryStories",        # Very high word counts
    "TalesFromTechSupport",   # Usually long and clean
    "IDontWorkHereLady",      # Great story lengths
    "legaladvice",            # Long, detailed explanations
    "talesfromyourserver",    # Good rants
    "AmItheAsshole",
    "tifu",
    "TrueOffMyChest",
    "confession",
    "offmychest",
    "relationship_advice",
    "stories",
    "AskReddit"
]
SUBREDDITS = [
    "
]


MIN_WORDS   = 1500
MAX_WORDS   = 15000
SEEN_FILE   = "seen_posts.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ---------------------------------------------------------------------------
# YouTube / Google AdSense Content Policy Filter
# Blocks posts containing content that violates YouTube's advertiser-friendly
# guidelines: sexual content, graphic violence, hate speech, drug promotion,
# dangerous acts, self-harm, and more.
# ---------------------------------------------------------------------------

# Each category contains (pattern, reason) tuples.
# Patterns use word boundaries (\b) where possible to reduce false positives.

BLOCKED_PATTERNS = {

    "sexual_content": [
        # Explicit acts / anatomy
        (r"\bsex\b",                        "sexual content"),
        (r"\bsexual\b",                     "sexual content"),
        (r"\bsexually\b",                   "sexual content"),
        (r"\bporn\b",                       "pornographic content"),
        (r"\bpornograph",                   "pornographic content"),
        (r"\bnude\b",                       "nudity"),
        (r"\bnudes\b",                      "nudity"),
        (r"\bnudity\b",                     "nudity"),
        (r"\bnaked\b",                      "nudity"),
        (r"\bbreasts?\b",                   "sexual content"),
        (r"\bnipple",                       "sexual content"),
        (r"\bpenis\b",                      "sexual content"),
        (r"\bvagina\b",                     "sexual content"),
        (r"\bgenitals?\b",                  "sexual content"),
        (r"\banal\b",                       "sexual content"),
        (r"\boral sex\b",                   "sexual content"),
        (r"\bhooking up\b",                 "sexual content"),
        (r"\bsleeping with\b",              "sexual content"),
        (r"\bone.night stand\b",            "sexual content"),
        (r"\bescort\b",                     "sexual content"),
        (r"\bprostitut",                    "sexual content"),
        (r"\bsexting\b",                    "sexual content"),
        (r"\bsext\b",                       "sexual content"),
        (r"\bfetish\b",                     "sexual content"),
        (r"\bkink\b",                       "sexual content"),
        (r"\bbdsm\b",                       "sexual content"),
        (r"\bstrip club\b",                 "sexual content"),
        (r"\bstriptease\b",                 "sexual content"),
        (r"\bonlyfans\b",                   "sexual content"),
        (r"\bcheating on\b",                "sexual content"),  # relationship cheating implying sex
        (r"\baffair\b",                     "sexual content"),
        (r"\binfidelity\b",                 "sexual content"),
        (r"\bslept with\b",                 "sexual content"),
        (r"\bhad sex\b",                    "sexual content"),
        (r"\bmasturbat",                    "sexual content"),
    ],

    "graphic_violence": [
        (r"\bmurder\b",                     "graphic violence"),
        (r"\bmurdered\b",                   "graphic violence"),
        (r"\bkilled\b",                     "graphic violence"),
        (r"\bkilling\b",                    "graphic violence"),
        (r"\bstabbed\b",                    "graphic violence"),
        (r"\bstabbing\b",                   "graphic violence"),
        (r"\bshooting\b",                   "graphic violence"),
        (r"\bshot\b",                       "graphic violence"),
        (r"\bgunshot\b",                    "graphic violence"),
        (r"\bblood\b",                      "graphic violence"),
        (r"\bbloody\b",                     "graphic violence"),
        (r"\bbeat.?up\b",                   "graphic violence"),
        (r"\bbeaten\b",                     "graphic violence"),
        (r"\bbeating\b",                    "graphic violence"),
        (r"\bbrutally\b",                   "graphic violence"),
        (r"\btorture\b",                    "graphic violence"),
        (r"\btortured\b",                   "graphic violence"),
        (r"\bfight\b",                      "graphic violence"),   # common but kept for safety
        (r"\bgore\b",                       "graphic violence"),
        (r"\bmutilat",                      "graphic violence"),
        (r"\bdecapitat",                    "graphic violence"),
        (r"\bassault\b",                    "graphic violence"),
        (r"\bassaulted\b",                  "graphic violence"),
        (r"\bchoked\b",                     "graphic violence"),
        (r"\bchoking\b",                    "graphic violence"),
        (r"\bstrangled\b",                  "graphic violence"),
        (r"\bstrangling\b",                 "graphic violence"),
        (r"\babuse\b",                      "graphic violence / abuse"),
        (r"\babused\b",                     "graphic violence / abuse"),
        (r"\bdomestic violence\b",          "graphic violence / abuse"),
    ],

    "self_harm_suicide": [
        (r"\bsuicid",                       "self-harm / suicide"),
        (r"\bself.?harm",                   "self-harm"),
        (r"\bcut.?myself\b",                "self-harm"),
        (r"\bkill.?myself\b",               "self-harm / suicide"),
        (r"\bwant.?to die\b",               "self-harm / suicide"),
        (r"\bending.?my life\b",            "self-harm / suicide"),
        (r"\boverdos",                       "self-harm / suicide"),
        (r"\bhanged.?myself\b",             "self-harm / suicide"),
        (r"\bjumped.?off\b",                "self-harm / suicide"),
        (r"\beating disorder\b",            "self-harm"),
        (r"\banorexia\b",                   "self-harm"),
        (r"\bbulimia\b",                    "self-harm"),
    ],

    "hate_speech": [
        (r"\bracist\b",                     "hate speech"),
        (r"\bracism\b",                     "hate speech"),
        (r"\bhate.?speech\b",               "hate speech"),
        (r"\bwhite supremac",               "hate speech"),
        (r"\bneo.?nazi\b",                  "hate speech"),
        (r"\bantisemit",                    "hate speech"),
        (r"\bislam[o]?phob",                "hate speech"),
        (r"\bhomophob",                     "hate speech"),
        (r"\btransphob",                    "hate speech"),
        (r"\bslur\b",                       "hate speech"),
        # Hard-coded slurs — pattern only, no readable word stored here
        (r"\bn[i!1]gg",                     "hate speech / slur"),
        (r"\bf[a@]gg[o0]t",                "hate speech / slur"),
        (r"\br[e3]tard",                    "hate speech / slur"),
    ],

    "drugs_and_alcohol": [
        (r"\bdrug dealer\b",                "drug promotion"),
        (r"\bdealing drugs\b",              "drug promotion"),
        (r"\bcocaine\b",                    "drug promotion"),
        (r"\bheroin\b",                     "drug promotion"),
        (r"\bmeth\b",                       "drug promotion"),
        (r"\bcrack\b",                      "drug promotion"),
        (r"\bfentanyl\b",                   "drug promotion"),
        (r"\bpills?\b",                     "drug promotion"),   # broad but flags common abuse context
        (r"\bgetting high\b",               "drug promotion"),
        (r"\bgot high\b",                   "drug promotion"),
        (r"\bweed\b",                       "drug promotion"),
        (r"\bmarijuana\b",                  "drug promotion"),
        (r"\bshrooms?\b",                   "drug promotion"),
        (r"\btripping\b",                   "drug promotion"),
        (r"\bblacked out\b",                "alcohol / drug abuse"),
        (r"\bgot drunk\b",                  "alcohol abuse"),
        (r"\bdrinking problem\b",           "alcohol abuse"),
        (r"\balcoholic\b",                  "alcohol abuse"),
    ],

    "dangerous_activities": [
        (r"\bbomb\b",                       "dangerous activity"),
        (r"\bexplosive\b",                  "dangerous activity"),
        (r"\bweapon\b",                     "dangerous activity"),
        (r"\bgun\b",                        "dangerous activity"),
        (r"\bfirearm\b",                    "dangerous activity"),
        (r"\bhack\b",                       "dangerous activity"),
        (r"\bstalking\b",                   "dangerous activity / harassment"),
        (r"\bstalked\b",                    "dangerous activity / harassment"),
        (r"\bscam\b",                       "dangerous activity / fraud"),
        (r"\bfraud\b",                      "dangerous activity / fraud"),
        (r"\bblackmail\b",                  "dangerous activity"),
        (r"\bextort",                       "dangerous activity"),
        (r"\bthreaten",                     "dangerous activity"),
        (r"\bterror",                       "dangerous activity"),
    ],

    "minors_safety": [
        (r"\bminor\b",                      "minor safety"),
        (r"\bchild.?abuse\b",               "minor safety"),
        (r"\bpedophil",                     "minor safety"),
        (r"\bunderaged?\b",                 "minor safety"),
        (r"\b13.?year.?old\b",              "minor safety"),
        (r"\b14.?year.?old\b",              "minor safety"),
        (r"\b15.?year.?old\b",              "minor safety"),
        (r"\b16.?year.?old\b",              "minor safety"),
        (r"\b17.?year.?old\b",              "minor safety"),
        (r"\bteenager.*sexual\b",           "minor safety"),
        (r"\bchild.*sexual\b",              "minor safety"),
    ],

    "profanity_heavy": [
        # Only the most egregious; mild swearing is not blocked by YouTube
        (r"\bf\*+ck",                       "heavy profanity"),
        (r"\bfuck\b",                       "heavy profanity"),
        (r"\bfucking\b",                    "heavy profanity"),
        (r"\bsh[i!1]t\b",                   "heavy profanity"),
        (r"\bbitch\b",                      "heavy profanity"),
        (r"\bass.?hole\b",                  "heavy profanity"),
        (r"\bcock\b",                       "heavy profanity"),
        (r"\bdick\b",                       "heavy profanity"),
        (r"\bcunt\b",                       "heavy profanity"),
        (r"\bpussy\b",                      "heavy profanity"),
        (r"\bbastard\b",                    "heavy profanity"),
        (r"\bdamn\b",                       "heavy profanity"),   # mild; remove if too aggressive
    ],
}

# Subreddits that are almost always NSFW / adult — skip entirely
BLOCKED_SUBREDDITS = {
    "sex",
    "nsfw",
    "gonewild",
    "adultery",
    "survivorsofabuse",
    "rape",
    "depression",
    "suicidewatch",
    "darkjokes",
}


def is_youtube_safe(title: str, body: str) -> tuple[bool, str]:
    """
    Returns (True, "") if the post passes all filters.
    Returns (False, reason) if a violation is found.

    Checks both title and body against every category of blocked patterns.
    """
    combined = (title + " " + body).lower()

    for category, patterns in BLOCKED_PATTERNS.items():
        for pattern, reason in patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                return False, f"[{category}] matched '{reason}' (pattern: {pattern})"

    return True, ""


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

    random_subs = SUBREDDITS.copy()
    random.shuffle(random_subs)

    filtered_count = 0  # track how many posts were blocked for reporting

    for subreddit in random_subs:
        # Skip entire subreddits that are inherently adult/unsafe
        if subreddit.lower() in BLOCKED_SUBREDDITS:
            print(f"⛔ Skipping blocked subreddit: r/{subreddit}")
            continue

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
            if content_node is None:
                continue

            # RSS Cleanup logic
            raw_text = html.unescape(content_node.text or "")
            raw_text = re.sub(r'<[^>]+>', ' ', raw_text)
            raw_text = re.sub(r'submitted by\s*/u/[\w-]+\s*', '', raw_text, flags=re.IGNORECASE)
            raw_text = raw_text.replace('[link]', '').replace('[comments]', '').strip()

            word_count = len(raw_text.split())
            if word_count < MIN_WORDS or word_count > MAX_WORDS:
                continue

            # ---------------------------------------------------------------
            # 🛡️ YOUTUBE CONTENT POLICY FILTER
            # Run BEFORE cleaning so raw text is checked (catches more cases)
            # ---------------------------------------------------------------
            safe, reason = is_youtube_safe(raw_title, raw_text)
            if not safe:
                filtered_count += 1
                print(f"   🚫 Filtered post ({reason}): {raw_title[:60]}")
                continue
            # ---------------------------------------------------------------

            # Clean and expand shorthand AFTER the safety check passes
            clean_title = clean_text(raw_title)
            clean_body  = clean_text(raw_text)
            voice       = pick_voice(clean_body)

            result = {
                "id":             post_id,
                "title":          clean_title,
                "text":           clean_body,
                "subreddit":      subreddit,
                "voice":          voice,
                "word_count":     word_count,
                "fetched_at":     datetime.utcnow().isoformat(),
                "posts_filtered": filtered_count,   # useful for debugging
            }

            with open("post.json", "w") as f:
                json.dump(result, f, indent=2)

            print(f"✅ Found Post: {clean_title[:50]}... in r/{subreddit}")
            print(f"   (Filtered {filtered_count} unsafe post(s) before finding this one)")
            return result

    print(f"❌ No new posts found. (Filtered {filtered_count} unsafe posts total)")
    sys.exit(1)

if __name__ == "__main__":
    fetch_best_post()
