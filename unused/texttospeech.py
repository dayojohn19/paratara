import edge_tts
import asyncio
import textwrap

async def main():
    text = """

In addition to our core services, we proudly offer a range of transportation options including carpooling, ride sharing, and shuttle services  all aimed at making travel more efficient and accessible for everyone. These solutions are designed to promote sustainability, reduce costs, and make every journey more convenient.

We also provide valuable advertising opportunities for our business partners, allowing them to showcase their products and services to a wider audience. And for new users, registration is simple and seamless  giving you instant access to all these features and more.

"""  # Your long content
    
    # Split into chunks (2000 chars per segment)
    chunks = textwrap.wrap(text, 2000)
    # voice = "fil-PH-BlessicaNeural"
    voice = "en-US-AriaNeural"
    
    for i, chunk in enumerate(chunks, 1):
        output_file = f"outputpartUS_{i}.mp3"
        communicate = edge_tts.Communicate(chunk, voice)
        await communicate.save(output_file)
        print(f"✅ Saved {output_file}")

asyncio.run(main())



# import pyttsx3
# engine = pyttsx3.init()
# engine.say("Hello, I am pyttsx3.")
# engine.runAndWait()

# engine.setProperty("rate", 150)        # speed
# engine.setProperty("volume", 1.0)      # 0.0 to 1.0

# voices = engine.getProperty("voices")
# engine.setProperty("voice", voices[1].id)  # switch male/female if available

# engine.say("This is a different voice.")
# engine.runAndWait()