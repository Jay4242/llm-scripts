#!/usr/bin/env python3

"""
A simple command‑line tool that sends a WAV audio file to an LLM backend
and prints the model’s response.

Usage:
    python llm-audio.py <audio_path> <prompt>

The script reads the audio file, base64‑encodes it, and sends it as an
`input_audio` message to the OpenAI-compatible API.
"""

import base64
import sys
from openai import OpenAI

# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python llm-audio.py <audio_path> <prompt>")
        sys.exit(1)

    path = sys.argv[1]
    prompt = sys.argv[2]

    # Choose the model you want to use.
    model = "Qwen2.5-Omni-3B-Q8_0"

    # Configure the client to point at the local Ollama server.
    client = OpenAI(base_url="http://localhost:9090/v1", api_key="none")

    # Read and base64‑encode the audio file.
    try:
        with open(path, "rb") as f:
            audio_bytes = f.read()
        base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as exc:
        print(f"Error reading audio file: {exc}")
        sys.exit(1)

    # Build the chat completion request.
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "input_audio",
                        "input_audio": {"data": base64_audio, "format": "wav"},
                    },
                ],
            },
        ],
        max_tokens=-1,
        stream=False,
        temperature=0.8,
    )

    # Print the assistant’s response.
    print(completion.choices[0].message.content.strip())

if __name__ == "__main__":
    main()
