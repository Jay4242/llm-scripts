#!/bin/python3

# Adapted from OpenAI's Vision example
from openai import OpenAI
import base64
import sys
import os
import httpx

# Point to the local server
client = OpenAI(base_url="http://localhost:9090/v1", api_key="none", timeout=httpx.Timeout(3600))

# Model selection
model = "gemma3:4b-it-q8_0"

# Retrieve the subtitle file path and image paths from the arguments
subtitle_file_path = sys.argv[2]
image_paths = sys.argv[3:]

# Create a list of filenames from the image paths
image_filenames = [os.path.basename(path) for path in image_paths]

# Retrieve the prompt from the arguments
prompt = sys.argv[1] + f" The images are: {', '.join(image_filenames)}"

# Prepare the messages for the LLM
messages = [
    {
        "role": "system",
        "content": "You are a helpful assistant.",
    },
    {
        "role": "user",
        "content": [{"type": "text", "text": prompt}],
    },
]

# Read each image, encode it to base64, and add it to the messages
for image_path in image_paths:
    try:
        with open(image_path.replace("'", ""), "rb") as image_file:
            image_data = image_file.read()
            base64_image = base64.b64encode(image_data).decode("utf-8")
            messages[1]["content"].append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                }
            )
    except FileNotFoundError:
        print(f"Couldn't read the image at {image_path}. Make sure the path is correct and the file exists.")
        exit()

# Read the subtitle file and add its content to the messages
try:
    with open(subtitle_file_path.replace("'", ""), "r") as subtitle_file:
        subtitle_text = subtitle_file.read()
        messages.append({
            "role": "user",
            "content": "These are the subtitles for the video:",
        })
        messages.append({
            "role": "user",
            "content": subtitle_text,
        })
except FileNotFoundError:
    print(f"Couldn't read the subtitle file at {subtitle_file_path}. Make sure the path is correct and the file exists.")
    exit()

# Send the messages to the LLM
completion = client.chat.completions.create(
    model=model,
    messages=messages,
    max_tokens=-1,
    stream=False,
)

# Print the response from the LLM
print(completion.choices[0].message.content.strip())
