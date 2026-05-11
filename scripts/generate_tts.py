import asyncio
import json
import edge_tts

def load_post():
    with open("post.json", "r") as f:
        return json.load(f)

async def generate(text, voice, audio_out, subtitle_out):
    communicate = edge_tts.Communicate(text, voice)
    submaker = edge_tts.SubMaker()

    with open(audio_out, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            # 🔧 FIX: We now look for both Word and Sentence boundaries!
            elif chunk["type"] in ["WordBoundary", "SentenceBoundary"]:
                submaker.feed(chunk)

    with open(subtitle_out, "w", encoding="utf-8") as f:
        f.write(submaker.get_srt())

    print(f"✅ Audio saved to {audio_out}")
    print(f"✅ Subtitles saved to {subtitle_out}")

if __name__ == "__main__":
    post = load_post()

    # Combine title + text for narration
    full_text = f"{post['title']}. {post['text']}"
    voice     = post["voice"]

    asyncio.run(generate(
        text=full_text,
        voice=voice,
        audio_out="audio.mp3",
        subtitle_out="captions.srt"
    ))
