#!/bin/python3

import sys
from openai import OpenAI

def get_user_input(prompt):
    return input(prompt)

def main():
    if len(sys.argv) != 5:
        print("Usage: python llm-conv.py <system> <file_path> <initial_prompt> <temperature>")
        sys.exit(1)

    system = sys.argv[1]
    file_path = sys.argv[2]
    initial_prompt = sys.argv[3]
    temp = float(sys.argv[4])

    # Point to the local server
    client = OpenAI(base_url="http://localhost:9090/v1", api_key="none")

    # Read the content of the document file
    try:
        with open(file_path, 'r') as file:
            file_content = file.read()
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' does not exist.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": file_content},
        {"role": "user", "content": initial_prompt}
    ]

    while True:
        # Get response from the model
        completion = client.chat.completions.create(
            model="llama-3.2-3b-it-q8_0",
            messages=messages,
            temperature=temp,
        )

        response_content = completion.choices[0].message.content.strip()
        print(f"Assistant: {response_content}")

        # Add assistant's response to the conversation
        messages.append({"role": "assistant", "content": response_content})

        # Get user input
        user_input = get_user_input("You: ")

        if user_input.lower() in ["exit", "quit"]:
            break

        # Add user input to the conversation
        messages.append({"role": "user", "content": user_input})

if __name__ == "__main__":
    main()
