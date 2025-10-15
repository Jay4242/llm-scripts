#!/bin/python3

import sys
# Example: reuse your existing OpenAI setup
from openai import OpenAI

# Expect two command‑line arguments:
#   1. System prompt
#   2. User prompt
system = sys.argv[1]
prompt = sys.argv[2]

# Point to the local server
client = OpenAI(base_url="http://localhost:9090/v1", api_key="None")

# Define a list of models to query
models = [
    {"name": "gemma-3-4b-it-q8_0", "temp": 1.0},
    {"name": "Qwen3-30B-A3B-Instruct-2507-Q8_0", "temp": 0.7},
    # Add more model entries here as needed
]

# Initialize conversation messages with system prompt and initial user prompt
messages = [
    {"role": "system", "content": system},
    {"role": "user", "content": prompt},
]
flipped_messages = messages

try:
    while True:
        for entry in models:
            model = entry["name"]
            temperature = entry.get("temp", 1.0)

            print(f"--- Model: {model} (temperature={temperature}) ---")
            completion = client.chat.completions.create(
                model=model,
                messages=flipped_messages,
                temperature=temperature,
                stream=True,
            )
            response = ""
            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    delta = chunk.choices[0].delta.content
                    print(delta, end="", flush=True)
                    response += delta
            print()  # newline after streaming

            # Append the assistant's response
            messages.append({"role": "assistant", "content": response.strip()})

            # Flip roles in the messages before sending to the model
            flipped_messages = [
                {
                    "role": ("assistant" if m["role"] == "user" else "user")
                    if m["role"] in ("assistant", "user")
                    else m["role"],
                    "content": m["content"],
                }
                for m in messages
            ]
except KeyboardInterrupt:
    print("\nInterrupted by user. Exiting gracefully.")
    sys.exit(0)
