import os
import urllib.request

def download_font(url, filename):
    if not os.path.exists(filename):
        print(f"Downloading {filename}...")
        # Add a headers to pretend we are a browser so GitHub doesn't block the request
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req) as response, open(filename, 'wb') as out_file:
                out_file.write(response.read())
            print(f"✅ {filename} downloaded.")
        except Exception as e:
            print(f"❌ Failed to download {filename}: {e}")
    else:
        print(f"ℹ️ {filename} already exists, skipping download.")

if __name__ == "__main__":
    # 🔧 FIX: Using the official Google Fonts raw GitHub link (much more reliable)
    ROBOTO_BOLD_URL = "https://github.com/google/fonts/raw/main/ofl/roboto/static/Roboto-Bold.ttf"
    
    download_font(ROBOTO_BOLD_URL, "Roboto-Bold.ttf")
