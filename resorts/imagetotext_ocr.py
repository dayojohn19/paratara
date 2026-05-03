import os
import asyncio
try:
    from google.cloud import vision
    GOOGLE_VISION_AVAILABLE = True
    GOOGLE_VISION_IMPORT_ERROR = None
except ImportError as e:
    GOOGLE_VISION_AVAILABLE = False
    GOOGLE_VISION_IMPORT_ERROR = e

# Initialize Google Cloud Vision client
# Make sure you have GOOGLE_APPLICATION_CREDENTIALS env variable set
print('Start extracting text from images...')
client = vision.ImageAnnotatorClient() if GOOGLE_VISION_AVAILABLE else None

async def extract_text_and_save(image_path):
    if not GOOGLE_VISION_AVAILABLE:
        raise RuntimeError(
            'Google Vision dependencies are not installed. Install google-cloud-vision.'
        ) from GOOGLE_VISION_IMPORT_ERROR

    # Read image file
    with open(image_path, 'rb') as image_file:
        content = image_file.read()
    
    # Create image object and perform text detection
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    
    # Extract the full text (first annotation contains all text)
    if texts:
        extracted_text = texts[0].description.strip()
    else:
        extracted_text = ""
    
    # Combine all detected text (already combined in first annotation)
    # extracted_text is already set above

    if not extracted_text.strip():
        extracted_text = "Walang nakitang teksto sa larawang ito."
        print(f"🖼️ {image_path} → No text detected")
    else:
        print(f"🖼️ {image_path} → Extracted: {extracted_text}")

    # Save extracted text next to image with suffix _ocr.txt
    output_file = os.path.splitext(image_path)[0] + "_ocr.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(extracted_text)

    print(f"✅ {image_path} → {output_file}")

async def main():
    folder = "storyimages"  # put your images here
    tasks = []
    for filename in os.listdir(folder):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            tasks.append(extract_text_and_save(os.path.join(folder, filename)))
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    if not GOOGLE_VISION_AVAILABLE:
        print('Google Vision dependency not installed; OCR script is disabled.')
    else:
        asyncio.run(main())
