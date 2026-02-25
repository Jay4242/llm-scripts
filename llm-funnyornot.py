#!/bin/python3

import sys
import argparse
from openai import OpenAI
import httpx
import json
import re

parser = argparse.ArgumentParser(description="LLM file processing script")
parser.add_argument("document_file_path", help="Path to the document file")
parser.add_argument("--movie", required=True, help="Movie title to analyze")
parser.add_argument("--rm-think", action="store_true", help="Remove <think>...</think> blocks from output")
args = parser.parse_args()

document_file_path = args.document_file_path
system = "You are a review analyzing bot, specifically one that determines if the reviewer thought the movie was funny or not. You always ONLY output in JSON with fields \"funny\" (a boolean) that is either set as True (if the review states or implies the movie was funny) or False (if the review states or implies the movie was NOT funny). Also a \"Reason\" field that will be a short text reason of why you decided on True/False. Do not give any preamble or further explanation outside of this JSON."
preprompt = f"The following is a review of {args.movie}:"
postprompt = "Determine if the reviewer thought the movie was funny or not."
temp = 1.0

# Read the content of the document file and split into individual reviews
try:
    with open(document_file_path, 'r') as file:
        full_text = file.read()
except FileNotFoundError:
    print(f"Error: The file '{document_file_path}' does not exist.")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

# Split reviews by the pattern "<number> out of <number> found this helpful"
review_pattern = re.compile(r'\d+\s+out\s+of\s+\d+\s+found\s+this\s+helpful')
matches = list(review_pattern.finditer(full_text))
reviews = []
prev_end = 0
for m in matches:
    end = m.end()
    reviews.append(full_text[prev_end:end].strip())
    prev_end = end
# If no matches were found, treat the whole file as a single review
if not reviews:
    reviews = [full_text.strip()]

# Point to the local server
client = OpenAI(base_url="http://localhost:9090/v1", api_key="none", timeout=httpx.Timeout(7200))

# Process each review independently
funny_counter = 0
for idx, review in enumerate(reviews, start=1):
    print(f"\n--- Processing review {idx}/{len(reviews)} ---\n")
    completion = client.chat.completions.create(
        model="qwen3:4b",
        messages=[
            {"role": "system", "content": system },
            {"role": "user", "content": preprompt },
            {"role": "user", "content": review },
            {"role": "user", "content": postprompt }
        ],
        temperature=temp,
        stream=True,
    )

    output = ""
    if args.rm_think:
        in_think = False
        think_buffer = ""

        for chunk in completion:
            if not (chunk.choices and chunk.choices[0].delta.content):
                continue
            text = chunk.choices[0].delta.content

            if think_buffer:
                text = think_buffer + text
                think_buffer = ""

            i = 0
            while i < len(text):
                if not in_think:
                    start_tag = text.find("<think>", i)
                    end_tag = text.find("</think>", i)

                    if start_tag == -1 and end_tag == -1:
                        print(text[i:], end="", flush=True)
                        output += text[i:]
                        break

                    if start_tag != -1 and (end_tag == -1 or start_tag < end_tag):
                        print(text[i:start_tag], end="", flush=True)
                        output += text[i:start_tag]
                        i = start_tag + len("<think>")
                        in_think = True
                        continue
                    else:
                        i = end_tag + len("</think>")
                        continue
                else:
                    end = text.find("</think>", i)
                    if end == -1:
                        think_buffer = text[i:]
                        break
                    i = end + len("</think>")
                    in_think = False
    else:
        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
                output += chunk.choices[0].delta.content
    print('\n')
    # Parse the JSON output and detect the "funny" field (case‑insensitive handling)
    try:
        # First attempt strict JSON parsing
        result = json.loads(output.strip())
    except json.JSONDecodeError:
        # Fallback: replace common Python‑style booleans with proper JSON literals
        fixed_output = output.strip().replace('True', 'true').replace('False', 'false')
        result = json.loads(fixed_output)

    # Normalise the "funny" value to a real bool, accepting strings of any case
    funny_raw = result.get("funny")
    if isinstance(funny_raw, bool):
        funny = funny_raw
    elif isinstance(funny_raw, str):
        lowered = funny_raw.lower()
        if lowered == "true":
            funny = True
        elif lowered == "false":
            funny = False
        else:
            funny = None
    else:
        funny = None

    if isinstance(funny, bool):
        funny_counter += 1 if funny else -1
        print(f"Detected funny: {funny}")
        print(f"Funny counter: {funny_counter}")
    else:
        print("Warning: 'funny' field missing or not a recognizable boolean")
print(f"Final funny counter: {funny_counter}")
