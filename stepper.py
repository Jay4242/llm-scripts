from openai import OpenAI
import httpx
import ast

MAX_STEPS = 10  # Maximum number of steps to prevent infinite loops

def make_llm_request(system_prompt, user_prompt, temperature):
    """
    Makes a request to the LLM and returns the content.

    Args:
        system_prompt (str): The system prompt for the LLM.
        user_prompt (str): The user prompt for the LLM.
        temperature (float): The temperature for the LLM.

    Returns:
        str: The content returned by the LLM, or None on error.
    """
    try:
        client = OpenAI(base_url="http://localhost:9090/v1", api_key="none", timeout=httpx.Timeout(3600))

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]

        completion = client.chat.completions.create(
            model="gemma-3-4b-it-q8_0",
            messages=messages,
            temperature=temperature,
            stream=True,
        )

        full_content = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_content += chunk.choices[0].delta.content

        # Remove lines with three backticks
        lines = full_content.splitlines()
        filtered_lines = [line for line in lines if "```" not in line]
        filtered_content = "\n".join(filtered_lines)

        return filtered_content
    except Exception as e:
        print(f"Error in make_llm_request: {e}")
        return None

def validate_array_length(llm_response, target_length):
    """
    Validates if the LLM response (assumed to be a string representation of an array)
    has the expected length.

    Args:
        llm_response (str): The LLM's response string.
        target_length (int): The expected length of the array.

    Returns:
        bool: True if the array length matches the target length, False otherwise.
    """
    if not isinstance(llm_response, str):
        print("Error: llm_response must be a string.")
        return False

    if not isinstance(target_length, int) or target_length < 0:
        print("Error: target_length must be a non-negative integer.")
        return False

    try:
        # Parse the LLM response as a Python list
        array = ast.literal_eval(llm_response)

        # Check if the parsed object is a list and has the expected length
        if isinstance(array, list) and len(array) == target_length:
            return True
        else:
            return False
    except (SyntaxError, ValueError) as e:
        print(f"Error parsing LLM response: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

def is_array(llm_response):
    """
    Checks if the LLM response is a valid Python list.

    Args:
        llm_response (str): The LLM's response string.

    Returns:
        bool: True if the response is a valid list, False otherwise.
    """
    if not isinstance(llm_response, str):
        print("Error: llm_response must be a string.")
        return False

    try:
        # Parse the LLM response as a Python list
        array = ast.literal_eval(llm_response)

        # Check if the parsed object is a list
        return isinstance(array, list)
    except (SyntaxError, ValueError) as e:
        print(f"Error parsing LLM response: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

def get_panic_attack_steps(temperature):
    """
    Prompts the LLM for an array of steps to take when suffering from a panic attack.

    Args:
        temperature (float): The temperature for the LLM.

    Returns:
        list: An array of steps to take when suffering from a panic attack.
    """
    system_prompt = "You are a helpful assistant that provides clear and concise instructions."
    user_prompt = "Please provide a python array of steps to take when suffering from a panic attack.  The list should be no more than 10 steps. Do not include any preamble or explanation with the array."
    llm_response = make_llm_request(system_prompt, user_prompt, temperature)

    if llm_response and is_array(llm_response):
        return ast.literal_eval(llm_response)
    else:
        print("LLM response was not a valid array or request failed.  Returning an empty list.")
        return []

def process_step(step, temperature):
    """
    Prompts the user for a response to the step, sends that response to the LLM,
    and returns the LLM's response.  Loops until the LLM confirms completion.

    Args:
        step (str): The current step.
        temperature (float): The temperature for the LLM.

    Returns:
        None
    """
    conversation_history = []
    step_completed = False
    for i in range(MAX_STEPS):  # Limit the number of iterations
        user_response = input(f"Step: {step}\nPlease provide a response indicating if you completed this step: ").lower()

        # Use LLM to determine if the step was completed
        completion_check_prompt = f"The user is experiencing a panic attack and is on this step: {step}. The user responded with: {user_response}.  Based on the user's response, do you think the user completed the step *exactly as instructed*? For example, if the step requires listing 5 things, did the user list exactly 5 things? Only answer ```yes``` or ```no```. It is very important that you are strict."
        completion_check_system_prompt = "You are an expert at determining if a user has completed a step in a panic attack recovery process. You must start your answer with ```Yes``` or ```No```.  Only respond with 'Yes' if the user completed the task in totality and exactly as instructed."

        llm_completion_check_response = make_llm_request(completion_check_system_prompt, completion_check_prompt, temperature)

        if llm_completion_check_response and llm_completion_check_response.lower().startswith("yes"):
            print("Great job!")
            step_completed = True
            break  # Exit the loop if the step is completed

        user_prompt = f"The user is experiencing a panic attack and is on this step: {step}. The user responded with: {user_response}.  Please provide a helpful and encouraging response."
        system_prompt = "You are a supportive and helpful assistant, specialized in helping people through panic attacks."

        llm_response = make_llm_request(system_prompt, user_prompt, temperature)

        if llm_response:
            conversation_history.append({"role": "user", "content": user_prompt})
            conversation_history.append({"role": "assistant", "content": llm_response})

            print(f"LLM Response: {llm_response}")
        else:
            print("LLM request failed.  Please try again.")

    if not step_completed:
        print("Maximum number of attempts reached for this step.")
    return

def main():
    """
    Main function to orchestrate the panic attack steps.
    """
    panic_attack_steps = get_panic_attack_steps(0.7)

    if panic_attack_steps:
        for step in panic_attack_steps:
            process_step(step, 0.7)
    else:
        print("No panic attack steps to process.")

if __name__ == '__main__':
    main()
