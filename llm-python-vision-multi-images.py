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
model = "Qwen3-VL-30B-A3B-Thinking"

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

# Add the text prompt to the messages (first)
messages[1]["content"].append({"type": "text", "text": prompt})

# Read each image, encode it to base64, and add it to the messages (after prompt)
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


# Send the messages to the LLM
completion = client.chat.completions.create(
    model=model,
    messages=messages,
    max_tokens=-1,
    stream=False,
    temperature=temperature, # New: Pass temperature
)

# Print the response from the LLM
# Get the raw response from the LLM
raw_output = completion.choices[0].message.content

# Extract any <think>...</think> block and print it to stderr
think_match = re.search(r'<think>(.*?)</think>', raw_output, flags=re.DOTALL)
if think_match:
    thinking_text = think_match.group(1).strip()
    print(f"Thinking Text: {thinking_text}", file=sys.stderr)
else:
    # No <think> block was found – still emit a message to stderr to confirm stderr is functional
    print("No thinking block detected.", file=sys.stderr)

# Remove any <think>...</think> block (including the newline after </think>) from the output
# The DOTALL flag allows '.' to match newlines so the entire block is removed
clean_output = re.sub(r'<think>.*?</think>\s*', '', raw_output, flags=re.DOTALL).strip()

print(clean_output)
