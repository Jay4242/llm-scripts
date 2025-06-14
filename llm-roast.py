import requests
from bs4 import BeautifulSoup
import re
import sys # Added for command-line arguments
from openai import OpenAI 
import httpx # Added for httpx.Timeout

def fetch_and_clean_html(url):
    """
    Fetches HTML from a given URL, cleans it using BeautifulSoup,
    and returns the prettified HTML content as a string.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        html_content = response.text

        soup = BeautifulSoup(html_content, 'html.parser')
        prettified_html = soup.prettify()
        return prettified_html

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during HTML fetching or cleaning: {e}")
        return None

def extract_person_details(html_content_string):
    """
    Reads cleaned HTML from a string and extracts specific details about the person.
    """
    if not html_content_string:
        print("No HTML content provided for extraction.")
        return None

    try:
        soup = BeautifulSoup(html_content_string, 'html.parser')

        details = {}

        # Extract Name and Profession
        name_tag = soup.find('h1', class_='type-34')
        if name_tag:
            details['Name'] = name_tag.text.strip()

        profession_tag = soup.find('p', class_='bio-module__profession')
        if profession_tag and profession_tag.a:
            details['Profession'] = profession_tag.a.text.strip()

        # Extract Person Attributes (Birthday, Birth Sign, Birthplace, Age)
        attributes_div = soup.find('div', class_='bio-module__person-attributes')
        if attributes_div:
            for p_tag in attributes_div.find_all('p'):
                spans = p_tag.find_all('span')
                if len(spans) == 2:
                    label = spans[0].text.strip().replace(':', '')
                    # Normalize whitespace for the value
                    value = re.sub(r'\s+', ' ', spans[1].text).strip()
                    details[label] = value

        # Extract About sections (About, Before Fame, Trivia, Family Life, Associated With)
        about_container = soup.find('div', class_='about-module')
        if about_container:
            current_heading = None
            for element in about_container.children:
                # Check if the element is a tag and not a NavigableString (whitespace, etc.)
                if hasattr(element, 'name'):
                    if element.name == 'h2':
                        current_heading = element.text.strip()
                        details[current_heading] = "" # Initialize with empty string
                    elif element.name == 'p' and current_heading:
                        # Normalize whitespace for paragraph content
                        paragraph_content = re.sub(r'\s+', ' ', element.text).strip()
                        # Append paragraph content to the current heading's value
                        if details[current_heading]:
                            details[current_heading] += "\n" + paragraph_content
                        else:
                            details[current_heading] = paragraph_content
                    # Stop processing if we hit the inline banners or video section
                    elif element.name == 'div' and ('inline-banners' in element.get('class', []) or 'video-thumbnail' in element.get('class', [])):
                        break
                    elif element.name == 'a' and 'video-thumbnail' in element.get('class', []):
                        break


        # Format the extracted details into a readable string
        output_string = ""
        if 'Name' in details:
            output_string += f"Name: {details['Name']}\n"
        if 'Profession' in details:
            output_string += f"Profession: {details['Profession']}\n"
        output_string += "\n--- Personal Details ---\n"
        for key in ['Birthday', 'Birth Sign', 'Birthplace', 'Age']:
            if key in details:
                output_string += f"{key}: {details[key]}\n"

        output_string += "\n--- Biography ---\n"
        for key in ['About', 'Before Fame', 'Trivia', 'Family Life', 'Associated With']:
            if key in details and details[key]:
                output_string += f"{key}:\n{details[key]}\n\n"

        return output_string.strip()

    except Exception as e:
        print(f"An unexpected error occurred during HTML parsing: {e}")
        return None

def generate_roast(person_info_string):
    """
    Generates a scathing roast using an LLM based on the provided person's information.
    """
    if not person_info_string:
        print("No person information provided to generate a roast.")
        return

    # LLM Configuration (similar to llm-python-file.py)
    client = OpenAI(base_url="http://localhost:9090/v1", api_key="none", timeout=httpx.Timeout(3600))
    model_name = "gemma-3-4b-it-q8_0" # This can be made configurable if needed
    temperature = 1.0 # This can be made configurable if needed

    # Define the prompts for the roast
    system_prompt = "You are a professional comedian known for your sharp wit and ability to deliver hilarious, yet biting, roasts. Your roasts are clever, insightful, and always land with a punch. Focus on the person's public persona, achievements, and any quirky details provided. Keep the roast concise, around 200-300 words. Do not include any stage directions, parenthetical notes, or audience interaction cues."
    pre_prompt = "I am going to provide you with detailed information about a public figure. Your task is to write a scathing, yet humorous, roast based on the provided details. Make sure to incorporate specific facts from the biography to make the roast personal and funny."
    post_prompt = "Now, deliver the roast. Make it sound like you're performing it live."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": pre_prompt},
        {"role": "user", "content": person_info_string}, # The extracted document
        {"role": "user", "content": post_prompt}
    ]

    print("\n--- Generating Roast (this may take a moment) ---")
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            stream=True,
        )

        for chunk in completion:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print('\n') # Add a newline at the end of the streamed output

    except Exception as e:
        print(f"An error occurred during LLM interaction: {e}")

if __name__ == '__main__':
    # The script now expects a URL as a command-line argument
    if len(sys.argv) < 2:
        print("Usage: python llm-roast.py <famousbirthdays.com_URL>")
        sys.exit(1)

    target_url = sys.argv[1] # Get URL from command line

    # First, fetch and clean the HTML, getting the content directly
    cleaned_html_content = fetch_and_clean_html(target_url)

    if cleaned_html_content:
        # Then, extract details from the cleaned HTML content string
        person_info = extract_person_details(cleaned_html_content)
        if person_info:
            print("\n--- Extracted Person Details ---")
            print(person_info)
            # Finally, generate the roast using the extracted information
            generate_roast(person_info)
        else:
            print("Failed to extract person details.")
    else:
        print("Failed to fetch or clean HTML content.")
