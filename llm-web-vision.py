#!/bin/python3

import sys
import base64
from openai import OpenAI
import httpx

# Get image path and text prompt from command line arguments
if len(sys.argv) < 3:
    print("Usage: llm-web-vision.py <image_path> <text_prompt>")
    sys.exit(1)

image_path = sys.argv[1]
text_prompt = sys.argv[2]

# Point to the local server
client = OpenAI(base_url="http://localhost:9090/v1", api_key="none", timeout=httpx.Timeout(3600))

# Read and encode the image to base64
try:
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")
except FileNotFoundError:
    print(f"Error: The file '{image_path}' does not exist.")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

# Create the message for the LLM
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
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            },
            {"type": "text", "text": text_prompt},
        ]
    }
]

# Send the message to the LLM
try:
    completion = client.chat.completions.create(
        model="gemma-3-4b-it-q8_0",
        messages=messages,
        max_tokens=-1,
        stream=True,
    )

    # Print the response from the LLM
    for chunk in completion:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print('\n')

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
