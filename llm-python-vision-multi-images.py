#!/bin/python3

# Adapted from OpenAI's Vision example
from openai import OpenAI
import base64
import sys
import os
import httpx
import re

# Point to the local server
client = OpenAI(
    base_url="http://localhost:9595/v1", api_key="none", timeout=httpx.Timeout(14400)
)

# Model selection
model = "Qwen3-VL-30B-A3B-Thinking"
is_qwen_model = "qwen" in model.lower()

QWEN_GENERAL_TASK_SETTINGS = {
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 20,
    "min_p": 0.0,
    "presence_penalty": 1.5,
    "repetition_penalty": 1.0,
}

# Retrieve the prompt, temperature, and image paths from the arguments
prompt = sys.argv[1]
temperature = float(sys.argv[2])  # New: Temperature argument
image_paths = sys.argv[3:]  # Shifted: Image paths start from 3rd argument

# Extract frame numbers from image paths
frame_numbers = []
for path in image_paths:
    match = re.search(r"frame_(\d+)\.jpg", path)
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
        "content": [],  # Initialize content as an empty list
    },
]

# Add the text prompt to the messages (first)
messages[1]["content"].append({"type": "text", "text": prompt})

# Read each image, encode it to base64, and add it to the messages (after prompt)
for image_path in image_paths:
    # Extract frame number from filename and normalize (e.g., frame_00123.jpg -> 123)
    _frame_match = re.search(r"frame_(\d+)\.jpg", image_path)
    _frame_num = int(_frame_match.group(1)) if _frame_match else "unknown"

    # Insert label before each image in "Frame N:" format
    messages[1]["content"].append({"type": "text", "text": f"Frame {_frame_num}:"})

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
        print(
            f"Couldn't read the image at {image_path}. Make sure the path is correct and the file exists."
        )
        exit()


# Send the messages to the LLM
request_kwargs = {
    "model": model,
    "messages": messages,
    "max_tokens": -1,
    "stream": True,
    "temperature": temperature,
    "thinking_budget_tokens": 10240,
}

if is_qwen_model:
    request_kwargs.update(
        {
            "temperature": QWEN_GENERAL_TASK_SETTINGS["temperature"],
            "top_p": QWEN_GENERAL_TASK_SETTINGS["top_p"],
            "presence_penalty": QWEN_GENERAL_TASK_SETTINGS["presence_penalty"],
            "extra_body": {
                "top_k": QWEN_GENERAL_TASK_SETTINGS["top_k"],
                "min_p": QWEN_GENERAL_TASK_SETTINGS["min_p"],
                "repetition_penalty": QWEN_GENERAL_TASK_SETTINGS[
                    "repetition_penalty"
                ],
            },
        }
    )

completion = client.chat.completions.create(**request_kwargs)

# Stream handling:
# - content tokens are streamed to stdout
# - reasoning_content (if provided) is streamed to stderr
# - <think>...</think> blocks in content are streamed to stderr and removed from stdout
OPEN_TAG = "<think>"
CLOSE_TAG = "</think>"

raw_output_parts = []
clean_output_parts = []
thinking_parts = []
pending = ""
in_think = False


def _emit_stdout(text: str):
    if text:
        clean_output_parts.append(text)
        print(text, end="", flush=True)
        print(text, end="", file=sys.stderr, flush=True)


def _emit_stderr(text: str):
    if text:
        thinking_parts.append(text)
        print(text, end="", file=sys.stderr, flush=True)


for chunk in completion:
    if not chunk.choices:
        continue

    delta = chunk.choices[0].delta

    delta_reasoning = getattr(delta, "reasoning_content", None)
    if delta_reasoning:
        _emit_stderr(delta_reasoning)

    delta_content = delta.content or ""
    if not delta_content:
        continue

    raw_output_parts.append(delta_content)
    pending += delta_content

    while pending:
        if in_think:
            close_idx = pending.find(CLOSE_TAG)
            if close_idx != -1:
                _emit_stderr(pending[:close_idx])
                pending = pending[close_idx + len(CLOSE_TAG) :]
                in_think = False
            else:
                keep = len(CLOSE_TAG) - 1
                if len(pending) > keep:
                    _emit_stderr(pending[:-keep])
                    pending = pending[-keep:]
                else:
                    break
        else:
            open_idx = pending.find(OPEN_TAG)
            if open_idx != -1:
                _emit_stdout(pending[:open_idx])
                pending = pending[open_idx + len(OPEN_TAG) :]
                in_think = True
            else:
                keep = len(OPEN_TAG) - 1
                if len(pending) > keep:
                    _emit_stdout(pending[:-keep])
                    pending = pending[-keep:]
                else:
                    break

# Flush any remaining buffered text at stream end
if pending:
    if in_think:
        _emit_stderr(pending)
    else:
        _emit_stdout(pending)

# Keep newline behavior clean for terminals/pipes
if clean_output_parts and not "".join(clean_output_parts).endswith("\n"):
    print()
    print(file=sys.stderr)

# If neither explicit reasoning_content nor <think> output appeared, preserve prior stderr signal
if not thinking_parts:
    print("No thinking block detected.", file=sys.stderr)
