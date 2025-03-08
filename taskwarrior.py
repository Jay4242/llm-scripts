#!/usr/bin/env python3

import subprocess
import json
import sys
from openai import OpenAI
import httpx
import os

class TaskWarrior:
    def __init__(self, task_binary='task'):
        self.task_binary = task_binary

    def execute(self, args):
        """Executes the task command with the given arguments."""
        try:
            process = subprocess.run(
                [self.task_binary] + args,
                capture_output=True,
                text=True,
                check=True
            )
            return process.stdout.strip() , None  # Return stdout, no error
        except subprocess.CalledProcessError as e:
            return None, e.stderr.strip()  # Return no stdout, return stderr
        except FileNotFoundError:
            return None, f"Error: Taskwarrior binary not found at {self.task_binary}"
        except Exception as e:
            return None, str(e)


    def add(self, description, **kwargs):
        """Adds a new task with the given description and optional attributes."""
        args = ['add', description]
        for key, value in kwargs.items():
            args.append(f'{key}:{value}')
        return self.execute(args)

    def list(self, filter_terms=None):
        """Lists tasks, optionally filtered by the given terms."""
        args = ['list']
        if filter_terms:
            args.extend(filter_terms)
        return self.execute(args)

    def complete(self, task_id):
        """Marks a task as complete."""
        return self.execute([str(task_id), 'done'])

    def get_task_data(self, filter_terms=None):
        """Returns task data in JSON format."""
        args = ['export']
        if filter_terms:
            args.extend(filter_terms)
        stdout, stderr = self.execute(args)
        if stdout:
            try:
                return json.loads(stdout), None
            except json.JSONDecodeError as e:
                return None, f"Error decoding JSON: {e}"
        else:
            return None, stderr

    def run_command(self, args):
        """Runs an arbitrary taskwarrior command."""
        return self.execute(args)

    def _stream_completion(self, system_prompt, pre_prompt, user_input, post_prompt, temp):
        """Streams a completion from a local LLM server."""
        client = OpenAI(base_url="http://localhost:9090/v1", api_key="none", timeout=httpx.Timeout(3600))

        completion = client.chat.completions.create(
            model="llama-3.2-3b-it-q8_0",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": pre_prompt},
                {"role": "user", "content": user_input},
                {"role": "user", "content": post_prompt}
            ],
            temperature=temp,
            stream=True,
        )

        for chunk in completion:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print('\n')

    def update_user(self):
        """Gets the most urgent task and provides the user with instructions on how to complete it."""

        system_prompt = """You are a helpful assistant that provides instructions to the user on how to complete their most urgent task.
        Pay close attention to the due date.
        If the task is overdue, insist that the task is urgent and needs to be completed immediately.
        If the task is due soon, tell them to prepare for it.
        If the task is far off, tell them to schedule time for it.
        Be concise and helpful."""
        pre_prompt = "Here is the most urgent task:"
        post_prompt = "What instructions would you give to the user to complete this task? Respond with natural language."
        temperature = 0.7

        # Get the most urgent task info
        stdout, stderr = self.get_most_urgent_task_info()
        if stderr:
            print(f"Error getting most urgent task info: {stderr}", file=sys.stderr)
            return

        print("Instructions for Most Urgent Task:")
        self._stream_completion(system_prompt, pre_prompt, stdout, post_prompt, temperature)

    def get_most_urgent_task_info(self):
        """Gets the most urgent task and returns its information."""

        system_prompt = """You are a taskwarrior expert.
        '-4d' means the task is 4 days overdue.
        Taskwarrior calculates urgency based on priority, due date, and dependencies.
        '+tag' means a tag is added, '-tag' means a tag is removed.
        Dates can be relative (e.g., 'tomorrow', 'eom') or absolute (e.g., '2024-01-01').
        Projects can be hierarchical (e.g., 'Project.Subproject').
        A negative due date means the task is overdue, a positive due date means the task is upcoming."""
        pre_prompt = "Here is my TaskWarrior output:"
        post_prompt = "Which task is most urgent? List only one, and include all of its details, all on one line, with no other text. Respond with only the task details."
        temperature = 0.0

        # Get the most urgent task
        stdout, stderr = self.execute(['next'])
        if stderr:
            return None, stderr

        # Capture the output of _stream_completion
        import io
        from contextlib import redirect_stdout
        f = io.StringIO()
        with redirect_stdout(f):
            self._stream_completion(system_prompt, pre_prompt, stdout, post_prompt, temperature)
        output = f.getvalue().strip()

        return output, None

    def generate_task_command(self, natural_language_request, temp):
        """Generates a taskwarrior command from a natural language request using a local LLM server."""

        system_prompt = """You are a taskwarrior expert. I will provide you with a natural language request, and you will respond with the correct taskwarrior command syntax to accomplish the request.
        You must respond with the correct taskwarrior command syntax to accomplish the request.
        Use the following guidelines when creating the command:
        * Dates must be in the format YYYY-MM-DD.
        * Times must be in 24 hour format, and are specified using the scheduled: attribute.
        * The 'add' command should be used.
        * The description must be quoted if it contains a capital letter.
        Do not include any explanation or other text, only the command."""
        pre_prompt = "You are a taskwarrior expert. I will provide you with a natural language request, and you will respond with the correct taskwarrior command syntax to accomplish the request."
        post_prompt = "\n\nHere is my request: " + natural_language_request + "\n\nWhat is the correct taskwarrior command to accomplish this? Respond with only the command."
        temperature = temp

        # Read the contents of taskwarrior.md
        try:
            with open("taskwarrior.md", "r") as f:
                taskwarrior_md_content = f.read()
        except FileNotFoundError:
            print("Error: taskwarrior.md not found.", file=sys.stderr)
            return
        except Exception as e:
            print(f"Error reading taskwarrior.md: {e}", file=sys.stderr)
            return

        generated_command = ""
        client = OpenAI(base_url="http://localhost:9090/v1", api_key="none", timeout=httpx.Timeout(3600))
        for chunk in client.chat.completions.create(
            model="llama-3.2-3b-it-q8_0",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": pre_prompt},
                {"role": "user", "content": taskwarrior_md_content},
                {"role": "user", "content": post_prompt}
            ],
            temperature=temperature,
            stream=True,
        ):
            if chunk.choices[0].delta.content:
                generated_command += chunk.choices[0].delta.content
                print(chunk.choices[0].delta.content, end="", flush=True)
        print('\n')

        # Ask the user if they want to add the task
        add_task = input("Add this task to Taskwarrior? (y/n): ")
        if add_task.lower() == 'y':
            # Execute the task command
            stdout, stderr = self.execute(generated_command.split())
            if stdout:
                print(stdout)
            if stderr:
                print(f"Error: {stderr}", file=sys.stderr)
        else:
            print("Task not added.")


if __name__ == '__main__':
    tw = TaskWarrior()

    # Display the most urgent task
    output, error = tw.execute(['next'])
    if output:
        print(output)
    if error:
        print(f"Error: {error}", file=sys.stderr)
    print('\n')

    # Example usage of update_user
    tw.update_user()

    # Example usage of get_most_urgent_task_info
    #tw.get_most_urgent_task_info()

    # Example usage of generate_task_command
    #tw.generate_task_command("create an appointment at March 28th 2025 at 2:00pm for 'IncomeTaxes'", 0.0)
