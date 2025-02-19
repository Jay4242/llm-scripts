#!/bin/python3

import sys
from openai import OpenAI
import pygame
import pygame.freetype

def get_user_input(prompt):
    return input(prompt)

def main():
    if len(sys.argv) != 6:
        print("Usage: python llm-conv.py <system> <file_path> <subject_line> <initial_prompt> <temperature>")
        sys.exit(1)

    # Initialize Pygame
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("LLM Conversation")
    font = pygame.freetype.Font(None, 24)
    clock = pygame.time.Clock()

    # Colors
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)

    system = sys.argv[1]
    file_path = sys.argv[2]
    subject_line = sys.argv[3]
    initial_prompt = sys.argv[4]
    temp = float(sys.argv[5])

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
        {"role": "user", "content": subject_line},
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

        # Render assistant's response in Pygame
        text_surface, rect = font.render(f"Assistant: {response_content}", WHITE)
        screen.blit(text_surface, (10, rect.height * (len(messages) - 1)))
        pygame.display.flip()

        # Add assistant's response to the conversation
        messages.append({"role": "assistant", "content": response_content})

        # Get user input
        user_input = get_user_input("You: ")

        # Render user input in Pygame
        text_surface, rect = font.render(f"You: {user_input}", WHITE)
        screen.blit(text_surface, (10, rect.height * len(messages)))
        pygame.display.flip()

        if user_input.lower() in ["exit", "quit"]:
            break

        # Handle Pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # Add user input to the conversation
        messages.append({"role": "user", "content": user_input})

if __name__ == "__main__":
    main()
    pygame.quit()
