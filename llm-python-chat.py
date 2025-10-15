#!/bin/python3

import sys
# Example: reuse your existing OpenAI setup
from openai import OpenAI

system = sys.argv[1]
prompt = sys.argv[2]
temp = sys.argv[3]

temp = float(temp)

# Point to the local server
client = OpenAI(base_url="http://localhost:9090/v1", api_key="None")

completion = client.chat.completions.create(
  model="gemma-3-4b-it-q8_0",
  messages=[
    {"role": "system", "content": system },
    {"role": "user", "content": prompt }
  ],
  temperature=temp,
)

print(completion.choices[0].message.content.strip())
