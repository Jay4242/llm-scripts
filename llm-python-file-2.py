#!/bin/python3

import sys
# Example: reuse your existing OpenAI setup
from openai import OpenAI
import httpx

def read_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' does not exist.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

file1_path = sys.argv[1]
file2_path = sys.argv[2]
system = sys.argv[3]
preprompt1 = sys.argv[4]
postprompt1 = sys.argv[5]
postprompt2 = sys.argv[6]
temp = sys.argv[7]
temp = float(temp)

file1_content = read_file(file1_path)
file2_content = read_file(file2_path)


# Point to the local server
client = OpenAI(base_url="http://localhost:9090/v1", api_key="none", timeout=httpx.Timeout(3600))

completion = client.chat.completions.create(
  model="llama-3.2-3b-it-q8_0",
  messages=[
    {"role": "system", "content": system },
    {"role": "user", "content": preprompt1 },
    {"role": "user", "content": file1_content },
    {"role": "user", "content": postprompt1 },
    {"role": "user", "content": file2_content },
    {"role": "user", "content": postprompt2 }
  ],
  temperature=temp,
)

print(completion.choices[0].message.content.strip())
