from PIL import Image, ImageDraw, ImageFont
import json
import os
import urllib.request
import textwrap

def download_font(urls, filename):
    """Tries to download a font from a list of possible URLs."""
    if os.path.exists(filename):
        return True
    
    print(f"Attempting to download {filename}...")
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
    urllib.request.install_opener(opener)

    for url in urls:
        try:
            print(f"  Trying: {url}")
            urllib.request.urlretrieve(url, filename)
            print(f"  ✅ Successfully downloaded {filename}")
            return True
        except Exception as e:
            print(f"  ❌ Failed to download from this source: {e}")
            continue
    
    print(f"🔥 Critical Error: Could not download {filename} from any source.")
    return False

def generate_card():
    # 🔧 STABLE LINKS: Using CDN links which are much less likely to break than GitHub raw paths
    bold_urls = [
        "https://cdnjs.cloudflare.com/ajax/libs/roboto-fontface/0.10.0/fonts/roboto/Roboto-Bold.ttf",
        "https://github.com/google/fonts/raw/main/ofl/roboto/static/Roboto-Bold.ttf" # Backup
    ]
    reg_urls = [
        "https://cdnjs.cloudflare.com/ajax/libs/roboto-fontface/0.10.0/fonts/roboto/Roboto-Regular.ttf",
        "https://github.com/google/fonts/raw/main/ofl/roboto/static/Roboto-Regular.ttf" # Backup
    ]
    
    if not download_font(bold_urls, "Roboto-Bold.ttf") or not download_font(reg_urls, "Roboto-Regular.ttf"):
        # If we can't get Roboto, we try to use a default font later, but we need the files for FFmpeg too.
        print("⚠️ Proceeding without custom fonts. Captions might fall back to Arial.")

    # Load the post data
    if not os.path.exists("post.json"):
        print("❌ Error: post.json not found!")
        return

    with open("post.json", "r") as f:
        post = json.load(f)

    # Setup fonts with a safety fallback
    try:
        font_sub = ImageFont.truetype("Roboto-Bold.ttf", 32)
        font_user = ImageFont.truetype("Roboto-Regular.ttf", 28)
        font_title = ImageFont.truetype("Roboto-Bold.ttf", 46)
        font_footer = ImageFont.truetype("Roboto-Bold.ttf", 30)
    except:
        print("Falling back to default system font for the card image.")
        font_sub = font_user = font_title = font_footer = ImageFont.load_default()

    # Wrap title
    title_text = post.get("raw_title", post.get("title", "Reddit Post"))
    wrapped_title = textwrap.wrap(title_text, width=38)
    
    header_height = 120
    title_line_height = 60
    footer_height = 80
    padding = 60
    
    card_width = 940
    card_height = header_height + (len(wrapped_title) * title_line_height) + footer_height + (padding * 2)

    # Create a fully transparent 1080x1920 canvas
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    x_start = (1080 - card_width) // 2
    y_start = (1920 - card_height) // 2

    # Draw the Dark Mode Card Background
    draw.rounded_rectangle(
        [x_start, y_start, x_start + card_width, y_start + card_height], 
        radius=30, 
        fill="#1A1A1B", 
        outline="#343536", 
        width=3
    )

    # Draw Header
    avatar_x = x_start + padding
    avatar_y = y_start + padding
    draw.ellipse([avatar_x, avatar_y, avatar_x + 60, avatar_y + 60], fill="#FF4500")
    
    text_x = avatar_x + 85
    subreddit = post.get("subreddit", "reddit")
    draw.text((text_x, avatar_y + 2), f"r/{subreddit}", fill="#FFFFFF", font=font_sub)
    draw.text((text_x, avatar_y + 38), f"u/{post.get('author', 'user')} • 5h", fill="#818384", font=font_user)

    # Draw Title
    current_y = avatar_y + 100
    for line in wrapped_title:
        draw.text((x_start + padding, current_y), line, fill="#F2F2F2", font=font_title)
        current_y += title_line_height

    # Draw Footer
    footer_y = current_y + 30
    score = post.get("score", "15.2k")
    footer_text = f"⇧  {score}  ⇩        💬 Comments        ➦ Share"
    draw.text((x_start + padding, footer_y), footer_text, fill="#818384", font=font_footer)

    img.save("card.png")
    print("✅ Reddit card image generated successfully!")

if __name__ == "__main__":
    generate_card()
