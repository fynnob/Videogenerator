from PIL import Image, ImageDraw, ImageFont
import json
import os
import urllib.request
import textwrap

def download_font(url, filename):
    if not os.path.exists(filename):
        print(f"Downloading {filename}...")
        urllib.request.urlretrieve(url, filename)

def generate_card():
    # 1. Download sleek, modern fonts (Roboto)
    download_font("https://github.com/google/fonts/raw/main/ofl/roboto/Roboto-Bold.ttf", "Roboto-Bold.ttf")
    download_font("https://github.com/google/fonts/raw/main/ofl/roboto/Roboto-Regular.ttf", "Roboto-Regular.ttf")

    # 2. Load the post data
    with open("post.json", "r") as f:
        post = json.load(f)

    # 3. Setup fonts
    font_sub = ImageFont.truetype("Roboto-Bold.ttf", 32)
    font_user = ImageFont.truetype("Roboto-Regular.ttf", 28)
    font_title = ImageFont.truetype("Roboto-Bold.ttf", 46)
    font_footer = ImageFont.truetype("Roboto-Bold.ttf", 30)

    # 4. Calculate heights and wrap text
    # Wrap title at ~38 characters so it doesn't spill off the card
    wrapped_title = textwrap.wrap(post["raw_title"], width=38)
    
    header_height = 120
    title_line_height = 60
    footer_height = 80
    padding = 60
    
    card_width = 940
    card_height = header_height + (len(wrapped_title) * title_line_height) + footer_height + (padding * 2)

    # 5. Create a fully transparent 1080x1920 canvas
    img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Calculate center position
    x_start = (1080 - card_width) // 2
    y_start = (1920 - card_height) // 2

    # 6. Draw the Dark Mode Card Background (Rounded Rectangle)
    draw.rounded_rectangle(
        [x_start, y_start, x_start + card_width, y_start + card_height], 
        radius=30, 
        fill="#1A1A1B",       # Reddit Dark Gray
        outline="#343536",    # Subtle border
        width=3
    )

    # 7. Draw Header (Avatar, Subreddit, Username)
    avatar_x = x_start + padding
    avatar_y = y_start + padding
    draw.ellipse([avatar_x, avatar_y, avatar_x + 60, avatar_y + 60], fill="#FF4500") # Reddit Orange Avatar
    
    text_x = avatar_x + 85
    draw.text((text_x, avatar_y + 2), f"r/{post['subreddit']}", fill="#FFFFFF", font=font_sub)
    draw.text((text_x, avatar_y + 38), "u/throwaway • 5h", fill="#818384", font=font_user)

    # 8. Draw the Title
    current_y = avatar_y + 100
    for line in wrapped_title:
        draw.text((x_start + padding, current_y), line, fill="#F2F2F2", font=font_title)
        current_y += title_line_height

    # 9. Draw the Footer (Upvotes, Comments, Share)
    footer_y = current_y + 30
    score = post.get("score", "14.5k")
    footer_text = f"⇧  {score}  ⇩        💬 128 Comments        ➦ Share"
    draw.text((x_start + padding, footer_y), footer_text, fill="#818384", font=font_footer)

    # 10. Save the transparent overlay
    img.save("card.png")
    print("✅ Reddit card image generated successfully!")

if __name__ == "__main__":
    generate_card()
