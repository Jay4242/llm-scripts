import sys
from pyboy import PyBoy
from PIL import Image
import base64
from openai import OpenAI
import httpx
import time

if len(sys.argv) < 2:
    print("Usage: llm-pyboy.py <rom_file>")
    sys.exit(1)

rom_file = sys.argv[1]

try:
    pyboy = PyBoy(rom_file)
    # Initial warm-up period
    for _ in range(1200):
        pyboy.tick()

    # Point to the local server
    client = OpenAI(base_url="http://localhost:9090/v1", api_key="none", timeout=httpx.Timeout(3600))

    while True:
        # Move forward a few frames
        for _ in range(1200):
            pyboy.tick()
        screen = pyboy.screen.image

        # Convert the PIL image to base64
        import io
        buffered = io.BytesIO()
        screen.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        # Prompt for the text to send with the screenshot
        prompt_text = input("Enter prompt for the image: ")

        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that can understand images."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_str}"}
                    },
                    {"type": "text", "text": prompt_text},
                ]
            }
        ]

        completion = client.chat.completions.create(
            model="gemma-3-4b-it-q8_0",
            messages=messages,
            max_tokens=-1,
            stream=True,
        )

        # Print the response from the LLM
        print("LLM Response: ", end="", flush=True)
        for chunk in completion:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print('\n')

        time.sleep(1) # Add a delay to avoid overwhelming the LLM

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
