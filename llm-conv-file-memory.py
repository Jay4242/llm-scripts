#!/bin/python3

import sys
from openai import OpenAI

def get_user_input(prompt):
    return input(prompt)

def check_for_document_changes(client, file_path, user_input, file_content, temp):
    check_messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"Document content:\n{file_content}\n\nUser input:\n{user_input}\n\nDoes the user input contain information we should save in the Document Content to help the user in the future? Answer with 'Yes' or 'No'."},
    ]

    # Get response from the model
    completion = client.chat.completions.create(
        model="llama-3.2-3b-it-q8_0",
        messages=check_messages,
        temperature=temp,
    )

    response_content = completion.choices[0].message.content.strip()
    print(f"Change Check: {response_content}")

    if response_content.startswith("Yes"):
        # Get the suggested changes
        change_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Document content:\n{file_content}\n\nUser input:\n{user_input}\n\nWhat changes should be made to the document to help you assist the user in the future?\n\nONLY output what should be added. Do NOT output any explanation or any prepended text.  ONLY output the text that should be appended to the document."},
        ]

        # Get response from the model
        change_completion = client.chat.completions.create(
            model="llama-3.2-3b-it-q8_0",
            messages=change_messages,
            temperature=temp,
        )

        change_response_content = change_completion.choices[0].message.content.strip()
        print(f"Suggested Changes: {change_response_content}")

        # Append the changes to the document file
        with open(file_path, 'a') as file:
            file.write("\n" + change_response_content)

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

        # Check for document changes
        check_for_document_changes(client, file_path, user_input, file_content, temp)

        # Add user input to the conversation
        messages.append({"role": "user", "content": user_input})

if __name__ == "__main__":
    main()
