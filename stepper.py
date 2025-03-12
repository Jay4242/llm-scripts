from openai import OpenAI
import httpx
import ast

def make_llm_request(system_prompt, user_prompt, temperature, conversation_history=None):
    """
    Makes a request to the LLM and returns the content.

    Args:
        system_prompt (str): The system prompt for the LLM.
        user_prompt (str): The user prompt for the LLM.
        temperature (float): The temperature for the LLM.
        conversation_history (list, optional): A list of previous messages in the conversation. Defaults to None.

    Returns:
        str: The content returned by the LLM.
    """
    client = OpenAI(base_url="http://localhost:9090/v1", api_key="none", timeout=httpx.Timeout(3600))

    messages = [{"role": "system", "content": system_prompt}]

    if conversation_history:
        messages.extend(conversation_history)

    messages.append({"role": "user", "content": user_prompt})

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
            #print(chunk.choices[0].delta.content, end="", flush=True)
    #print('\n')

    # Remove lines with three backticks
    lines = full_content.splitlines()
    filtered_lines = [line for line in lines if "```" not in line]
    filtered_content = "\n".join(filtered_lines)

    return filtered_content

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

    if is_array(llm_response):
        return ast.literal_eval(llm_response)
    else:
        print("LLM response was not a valid array.  Returning an empty list.")
        return []

def process_step(step, temperature):
    """
    Prompts the user for a response to the step, sends that response to the LLM,
    and returns the LLM's response.  Loops until the LLM confirms completion.

    Args:
        step (str): The current step.
        temperature (float): The temperature for the LLM.

    Returns:
        str: The LLM's response to the user's response.
    """
    conversation_history = []
    while True:
        user_response = input(f"Step: {step}\nPlease provide a response indicating if you completed this step: ").lower()

        # Use LLM to determine if the step was completed
        completion_check_prompt = f"The user is experiencing a panic attack and is on this step: {step}. The user responded with: {user_response}.  Based on the user's response, do you think the user completed the step? Answer 'yes' or 'no'."
        completion_check_system_prompt = "You are an expert at determining if a user has completed a step in a panic attack recovery process. You must respond with only 'yes' or 'no'.  Only respond with 'yes' if the user completed the task in totality."

        llm_completion_check_response = make_llm_request(completion_check_system_prompt, completion_check_prompt, temperature)

        if "yes" in llm_completion_check_response.lower():
            print("Great job!")
            return

        user_prompt = f"The user is experiencing a panic attack and is on this step: {step}. The user responded with: {user_response}.  Please provide a helpful and encouraging response."
        system_prompt = "You are a supportive and helpful assistant, specialized in helping people through panic attacks."

        llm_response = make_llm_request(system_prompt, user_prompt, temperature, conversation_history)

        conversation_history.append({"role": "user", "content": user_prompt})
        conversation_history.append({"role": "assistant", "content": llm_response})

        print(f"LLM Response: {llm_response}")

if __name__ == '__main__':

    # Example usage of get_panic_attack_steps:
    panic_attack_steps = get_panic_attack_steps(0.7)

    # Iterate through the panic attack steps and process each one
    for step in panic_attack_steps:
        process_step(step, 0.7)
