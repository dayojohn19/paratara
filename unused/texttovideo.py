import os
import ollama
from transformers import BlipProcessor, BlipForConditionalGeneration
from moviepy import VideoFileClip
from PIL import Image
import asyncio
import edge_tts
from groq import Groq
from pathlib import Path
# from openai import OpenAI
from openai import OpenAI
# openaiclient = OpenAI(api_key="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")

openaiclient = OpenAI(
  api_key="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"
)
client = Groq(api_key="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")
# ---------- SETTINGS ----------
VIDEO_PATH = "storyvideo/Unknown.mp4"     # your input video
STORY_TXT_PATH = "storyvideo/story.txt"      # output story text
AUDIO_PATH = "storyvideo/story.mp3"          # output spoken mp3
FOLDER_PATH = "storyvideo"  
# VOICE = "fil-PH-FemaleRoxanneNeural"  # Filipino female voice
VOICE = "fil-PH-BlessicaNeural"
RATE = "-5%"                      # slower pace
FPS_EXTRACT = 1                   # extract 1 frame per second
# -------------------------------

print("⏳ Loading BLIP model (first time may take a few minutes)...")
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

print(f"🎬 Reading video: {VIDEO_PATH}")
clip = VideoFileClip(VIDEO_PATH)

# # limit to 10 seconds to keep it fast
# clip = clip.subclip(0, min(clip.duration, 10))
# Limit to 10 seconds manually (newer MoviePy doesn’t use subclip)
clip_duration = min(clip.duration, 10)
print(f"📏 Clip duration: {clip_duration:.1f}s")

frames = [Image.fromarray(frame) for frame in clip.iter_frames(fps=FPS_EXTRACT)]
print(f"🖼️ Extracted {len(frames)} frames for captioning...")

supported_video_exts = [".mp4", ".mov", ".avi", ".mkv"]
supported_image_exts = [".jpg", ".jpeg", ".png", ".webp"]

 
captions = []
# for i, frame in enumerate(frames):
#     inputs = processor(frame, return_tensors="pt")
#     out = model.generate(**inputs, max_new_tokens=30)
#     caption = processor.decode(out[0], skip_special_tokens=True)
#     captions.append(caption)
#     print(f"🖼️ Frame {i+1}: {caption}")
for file_path in Path(FOLDER_PATH).glob("*"):
    if file_path.suffix.lower() in supported_video_exts:
        print(f"🎬 Processing video: {file_path.name}")
        clip = VideoFileClip(str(file_path))
        clip_duration = min(clip.duration, 10)
        print(f"📏 Clip duration: {clip_duration:.1f}s")
        frames = [Image.fromarray(frame) for frame in clip.iter_frames(fps=FPS_EXTRACT)]
        print(f"🖼️ Extracted {len(frames)} frames for captioning...")
        for i, frame in enumerate(frames):
            inputs = processor(frame, return_tensors="pt")
            out = model.generate(**inputs, max_new_tokens=30)
            caption = processor.decode(out[0], skip_special_tokens=True)
            captions.append(f"{caption}")
            print(f"🖼️ Frame {i+1}: {caption}")

    elif file_path.suffix.lower() in supported_image_exts:
        print(f"🖼️ Processing image: {file_path.name}")
        image = Image.open(file_path).convert("RGB")
        inputs = processor(image, return_tensors="pt")
        out = model.generate(**inputs, max_new_tokens=30)
        caption = processor.decode(out[0], skip_special_tokens=True)
        # captions.append(f"[{file_path.name}] {caption}")
        captions.append(f"{caption}")
        print(f"📸 {file_path.name}: {caption}")
print(f"📝 Generated {len(captions)} captions.")
print('captions:', captions)
print()


story = " ".join(captions)




duration_seconds = len(captions) * 4  # approx 4 seconds per caption
approx_words = int(duration_seconds * 2.3)
prompt = f"""
in tagalog
can you summarize this

{chr(10).join(captions)}
 in approximately {duration_seconds} seconds,
in approximate {approx_words} words? 

"""

# prompt = f"""
# Isulat ang isang maikling kuwentong pampelikula sa wikang Filipino,
# may temang pag-asa at pagbabago.
# Ang tagal ng narasyon ay humigit-kumulang {duration_seconds} segundo
# (o mga {approx_words} salita lamang).
# Gamitin ang istilo ng isang storyteller sa radyo.
# """

# response = openaiclient.chat.completions.create(
#     model="gpt-4o-mini",  # or "gpt-4o" if you have access
#     messages=[
#         {"role": "system", "content": "You are a poetic Filipino storyteller."},
#         {"role": "user", "content": prompt},
#     ],
# )
# story = response.choices[0].message.content
# response = ollama.chat(
#     model="llama3",
#     messages=[
#         {"role": "system", "content": "You are a poetic Filipino storyteller."},
#         {"role": "user", "content": "Isalaysay ang paglalakbay ng isang alon sa dagat."},
#     ],
# )
response = client.chat.completions.create(
    # model="llama3-8b-8192",
    model="llama-3.1-8b-instant",
    messages=[
        {"role": "system", "content": "you are a historian telling its story in tagalog."},
        {"role": "user", "content": prompt},
    ],
)
# story = response["message"]["content"]
story = response.choices[0].message.content

print("\n📝 Final Story:\n")
print("\n🎙️ Generated Story:\n")
print(story)


response = openaiclient.responses.create(
  model="gpt-5-nano",
  input=f"make this betetr '{story}' ",
  store=True,
)

story = response.output_text

# Save story text
with open(STORY_TXT_PATH, "w", encoding="utf-8") as f:
    f.write(story)
print(f"💾 Saved story text → {STORY_TXT_PATH}")

# ---------- NARRATE STORY ----------
async def narrate(text):
    print("🎙️ Generating Filipino narration...")
    communicate = edge_tts.Communicate(text, voice=VOICE, rate=RATE)
    await communicate.save(AUDIO_PATH)
    print(f"✅ Saved audio → {AUDIO_PATH}")

asyncio.run(narrate(story))