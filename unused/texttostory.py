import os
import asyncio
import edge_tts
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import torch

# Load image caption model
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

async def describe_and_narrate(image_path):
    # Generate a caption from image
    raw_image = Image.open(image_path).convert("RGB")
    inputs = processor(raw_image, return_tensors="pt")
    out = model.generate(**inputs)
    caption = processor.decode(out[0], skip_special_tokens=True)

    # Optional: add some storytelling flair
    story = f"Ito ang larawan ng {caption}. Marahil ay may magandang kwento sa likod nito."

    # Convert text to speech
    voice = "fil-PH-BlessicaNeural"
    output_file = os.path.splitext(image_path)[0] + ".mp3"
    tts = edge_tts.Communicate(story, voice)
    await tts.save(output_file)

    print(f"✅ {image_path} → {output_file}")

async def main():
    folder = "storyimages"  # put your images here
    tasks = []
    for filename in os.listdir(folder):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            tasks.append(describe_and_narrate(os.path.join(folder, filename)))
    await asyncio.gather(*tasks)

asyncio.run(main())
