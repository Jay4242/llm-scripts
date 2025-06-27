#!/bin/python3

# Adapted from OpenAI's Vision example
from openai import OpenAI
import base64
import sys
import os
import httpx
import re

# Point to the local server
client = OpenAI(base_url="http://localhost:9595/v1", api_key="none", timeout=httpx.Timeout(3600))

# Model selection
model = "gemma3:4b-it-q8_0"

# Retrieve the prompt, temperature, and image paths from the arguments
prompt = sys.argv[1]
temperature = float(sys.argv[2]) # New: Temperature argument
image_paths = sys.argv[3:]       # Shifted: Image paths start from 3rd argument

# Extract frame numbers from image paths
frame_numbers = []
for path in image_paths:
    match = re.search(r'frame_(\d+)\.jpg', path)
    if match:
        frame_numbers.append(int(match.group(1)))
    else:
        print(f"Could not extract frame number from {path}.  Exiting.")
        exit()

# Determine the image range
if frame_numbers:
    start_frame = min(frame_numbers)
    end_frame = max(frame_numbers)
    image_range = f"{start_frame}-{end_frame}"
else:
    image_range = "No images found"

# Append image range to the prompt
prompt += f" The images are frames {image_range}"

# Prepare the messages for the LLM
messages = [
    {
        "role": "system",
        "content": "You are a helpful assistant.",
    },
    {
        "role": "user",
        "content": [], # Initialize content as an empty list
    },
]

# Read each image, encode it to base64, and add it to the messages (first)
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

# Add the text prompt to the messages (last)
messages[1]["content"].append({"type": "text", "text": prompt})


# Send the messages to the LLM
completion = client.chat.completions.create(
    model=model,
    messages=messages,
    max_tokens=-1,
    stream=False,
    temperature=temperature, # New: Pass temperature
)

# Print the response from the LLM
print(completion.choices[0].message.content.strip())
