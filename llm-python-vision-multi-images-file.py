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

# Retrieve the prompt, temperature, subtitle file path, and image paths from the arguments
prompt = sys.argv[1]
temperature = float(sys.argv[2]) # New: Temperature argument
subtitle_file_path = sys.argv[3] # Shifted: Subtitle file path is now 3rd argument
image_paths = sys.argv[4:]       # Shifted: Image paths start from 4th argument

# Extract frame numbers from image paths, but only if the path looks like an image
frame_numbers = []
for path in image_paths:
    if re.search(r'\.jpg$', path, re.IGNORECASE):
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

# Add the text prompt to the messages (first)
messages[1]["content"].append({"type": "text", "text": prompt})
# Read each image, encode it to base64, and add it to the messages (first)
for image_path in image_paths:
    # Extract frame number for annotation
    _frame_match = re.search(r'frame_(\d+)\.jpg', image_path)
    _frame_num = _frame_match.group(1) if _frame_match else "unknown"
    # Add frame annotation text
    messages[1]["content"].append({"type": "text", "text": f"Frame: {_frame_num}"})
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
    temperature=temperature, # New: Pass temperature
)

# Print the response from the LLM
print(completion.choices[0].message.content.strip())
