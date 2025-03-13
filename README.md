# llm-scripts

A collection of scripts that leverage Large Language Models (LLMs) for various tasks.

## Getting Started

Before using these scripts, make sure you have the following:

*   Python 3.6 or higher
*   A local LLM server (e.g., llama-server) running and accessible.  The scripts are configured to connect to a server at `http://localhost:9090/v1` by default. You may need to set the `OPENAI_BASE_URL` environment variable if your server is running on a different address.
*   Required Python packages. You can install them using pip:

    ```bash
    pip install requests openai python-dotenv beautifulsoup4 httpx
    ```

## Script Categories

*   [Conversational AI](#conversational-ai)
*   [File Processing](#file-processing)
*   [Media Management](#media-management)
*   [Document Management](#document-management)
*   [Task Management](#task-management)
*   [Web Scraping](#web-scraping)
*   [Utilities](#utilities)

## Conversational AI

These scripts provide different ways to interact with LLMs in a conversational manner.

### `llm-conv.py`

**Description:** A script for conducting interactive conversations with an LLM.

**Purpose:** This script takes a system prompt, an initial user prompt, and a temperature value as input to start a chat session with the LLM.

**Usage:**

```bash
python llm-conv.py <system_prompt> <initial_prompt> <temperature>
```

*   `<system_prompt>`: A string that sets the context and behavior of the LLM (e.g., "You are a helpful assistant").
*   `<initial_prompt>`: The first message you send to the LLM to start the conversation.
*   `<temperature>`: A float value (e.g., 0.7) that controls the randomness of the LLM's responses. Higher values result in more creative and unpredictable outputs.

**Dependencies:**

*   `openai`
*   `httpx`

**Configuration:**

*   Ensure that a local LLM server is running and accessible. The script is configured to connect to a server at `http://localhost:9090/v1`. You may need to set the `OPENAI_BASE_URL` environment variable if your server is running on a different address.

**Example:**

```bash
python llm-conv.py "You are a helpful assistant" "Hello, how are you?" 0.7
```

**Note:** This script does not have built-in context length management.

### `llm-file-conv.py`

**Description:** Extends `llm-conv.py` by incorporating a file's content into the LLM's context.

**Purpose:** This script allows you to provide the LLM with the content of a file, enabling it to answer questions or perform tasks related to that content.

**Usage:**

```bash
python llm-file-conv.py <system_prompt> <file_path> <initial_prompt> <temperature>
```

*   `<system_prompt>`: Same as in `llm-conv.py`.
*   `<file_path>`: The path to the file whose content you want to include in the conversation.
*   `<initial_prompt>`: Same as in `llm-conv.py`.
*   `<temperature>`: Same as in `llm-conv.py`.

**Dependencies:**

*   `openai`
*   `httpx`

**Configuration:**

*   Same as `llm-conv.py`.

**Example:**

```bash
python llm-file-conv.py "You are a code reviewer" my_code.py "What potential bugs do you see in this code?" 0.6
```

**Note:** Make sure the file path is correct and accessible.

### `llm-file-conv-pygame.py`

**Description:** Combines the functionality of `llm-file-conv.py` with a Pygame interface.

**Purpose:** This script aims to display the conversation with the LLM in a graphical window using Pygame.

**Usage:**

```bash
python llm-file-conv-pygame.py <system_prompt> <file_path> <subject_line> <initial_prompt> <temperature>
```

*   `<system_prompt>`: Same as in `llm-file-conv.py`.
*   `<file_path>`: Same as in `llm-file-conv.py`.
*   `<subject line>`: A short description of the file's content.
*   `<initial_prompt>`: Same as in `llm-conv.py`.
*   `<temperature>`: Same as in `llm-conv.py`.

**Dependencies:**

*   `openai`
*   `httpx`
*   `pygame`

**Configuration:**

*   Same as `llm-conv.py`.

**Note:** The Pygame display functionality is currently incomplete and may not render the text correctly.

### `llm-conv-file-memory.py`

**Description:** Implements a memory mechanism for LLM conversations by updating a text file with relevant information from the conversation.

**Purpose:** This script aims to maintain a persistent memory of the conversation by allowing the LLM to suggest updates to a "memory" file.

**Usage:**

```bash
python llm-conv-file-memory.py <system_prompt> <file_path> <initial_prompt> <temperature>
```

*   `<system_prompt>`: Same as in `llm-file-conv.py`.
*   `<file_path>`: The path to the memory file.
*   `<initial_prompt>`: Same as in `llm-conv.py`.
*   `<temperature>`: Same as in `llm-conv.py`.

**Dependencies:**

*   `openai`
*   `httpx`

**Configuration:**

*   Same as `llm-conv.py`.

**How it works:**

1.  The script reads the content of the memory file.
2.  It sends the file content, along with the user's input, to the LLM.
3.  The LLM determines if the user's input contains information that should be added to the memory file.
4.  If the LLM decides to update the memory file, it suggests the changes.
5.  The script appends the suggested changes to the memory file.

## File Processing

These scripts process files using LLMs.

### `grammarai.py`

**Description:** Checks the grammar of a text file using an LLM.

**Purpose:** This script reads a text file, splits it into sentences, and uses an LLM to correct any grammatical errors in each sentence.

**Usage:**

```bash
python grammarai.py <file_path>
```

*   `<file_path>`: The path to the text file you want to check.

**Dependencies:**

*   `openai`
*   `dotenv`
*   `httpx`
*   `re`

**Configuration:**

*   Ensure that a local LLM server is running and accessible. The script is configured to connect to a server at `http://localhost:9090/v1`.

**Note:** The quality of the grammar correction depends on the capabilities of the LLM you are using.

### `llm-python-file.py`

**Description:** Sends a file's content to an LLM along with system, pre, and post prompts.

**Purpose:** This script reads the content of a specified file and sends it to a local LLM server, along with a system prompt, a pre-prompt, and a post-prompt. This allows you to process the file's content using the LLM with specific instructions.

**Usage:**

```bash
python llm-python-file.py <document_file_path> <system> <preprompt> <postprompt> <temp>
```

*   `<document_file_path>`: The path to the file whose content will be sent to the LLM.
*   `<system>`: The system prompt that sets the context for the LLM.
*   `<preprompt>`: The prompt that comes before the file content.
*   `<postprompt>`: The prompt that comes after the file content.
*   `<temp>`: The temperature setting for the LLM.

**Dependencies:**

*   `openai`
*   `httpx`
*   `sys`

**Configuration:**

*   Ensure that a local LLM server is running and accessible. The script is configured to connect to a server at `http://localhost:9090/v1`.

**Note:** This script is designed to work with local LLM servers that implement the OpenAI API.

### `llm-python-file-2.py`

**Description:** Sends two files' content to an LLM along with system, pre, and post prompts.

**Purpose:** This script reads the content of two specified files and sends them to a local LLM server, along with a system prompt, a pre-prompt, and a post-prompt before the first file, and a post-prompt after the first file and before the second file, and a final post-prompt after the second file. This allows you to process the files' content using the LLM with specific instructions.

**Usage:**

```bash
python llm-python-file-2.py <file1_path> <file2_path> <system> <preprompt1> <postprompt1> <postprompt2> <temp>
```

*   `<file1_path>`: The path to the first file whose content will be sent to the LLM.
*   `<file2_path>`: The path to the second file whose content will be sent to the LLM.
*   `<system>`: The system prompt that sets the context for the LLM.
*   `<preprompt1>`: The prompt that comes before the first file content.
*   `<postprompt1>`: The prompt that comes after the first file content.
*   `<postprompt2>`: The prompt that comes after the second file content.
*   `<temp>`: The temperature setting for the LLM.

**Dependencies:**

*   `openai`
*   `httpx`
*   `sys`

**Configuration:**

*   Ensure that a local LLM server is running and accessible. The script is configured to connect to a server at `http://localhost:9090/v1`.

**Note:** This script is designed to work with local LLM servers that implement the OpenAI API.

## Media Management

These scripts interact with media server applications.

### `llm_plex.py`

**Description:** Interacts with a local Plex media server to provide movie suggestions.

**Purpose:** This script automates the process of getting movie recommendations by fetching movie genres and unwatched movies from your Plex server, scraping movie data from Rotten Tomatoes, and using an LLM to suggest movies.

**Usage:**

1.  Set the `PLEX_API_KEY` environment variable with your Plex API key.
2.  Ensure that the `PLEX_URL` variable is set correctly (default: `http://plex.lan`).
3.  Run the script:

```bash
python llm_plex.py
```

**Dependencies:**

*   `requests`
*   `xml.etree.ElementTree`
*   `json`
*   `datetime`
*   `getpass`
*   `llm_rottentomatoes.py`

**Configuration:**

The script relies on environment variables for configuration:

*   `PLEX_URL`: The base URL of your Plex server (e.g., `http://plex.lan`).
*   `PLEX_LIBRARY_SECTION`: The library section ID for movies (default: `"1"`).
*   `LLM_BASE_URL`: The base URL of your local LLM server (e.g., `http://localhost:9090/v1`).
*   `LLM_MODEL`: The name of the LLM model to use (default: `"llama-3.2-3b-it-q8_0"`).
*   `DEFAULT_TEMPERATURE`: The default temperature for LLM queries (default: `0.7`).
*   `ROTTEN_TOMATOES_URL`: The URL for scraping Rotten Tomatoes data (default: `"https://www.rottentomatoes.com/browse/movies_at_home/sort:popular"`).

**Note:** This script requires that you have a local LLM server running and accessible and uses `llm_rottentomatoes.py` to scrape data from Rotten Tomatoes.

### `llm-plex.bash`

**Description:** Interacts with a local Plex media server to provide movie suggestions.

**Purpose:** This script automates the process of getting movie recommendations by fetching movie genres and unwatched movies from your Plex server, scraping movie data from Rotten Tomatoes, and using an LLM to suggest movies.

**Usage:**

1.  Set the `api` variable in the script to your Plex API key.
2.  Ensure that the `PLEX_URL` variable is set correctly (default: `http://plex.lan`).
3.  Run the script:

```bash
./llm-plex.bash
```

**Dependencies:**

*   `curl`
*   `jq`
*   `xmlstarlet`
*   `llm-python-file.py`
*   `llm-python-file-2.py`
*   `llm-rottentomatoes.bash`

**Note:** This script requires that you have a local LLM server running and accessible and uses several helper scripts (`llm-python-file.py`, `llm-python-file-2.py`, and `llm-rottentomatoes.bash`) to interact with the LLM and scrape data from Rotten Tomatoes.

### `tubearchivist.py`

**Description:** Interacts with a TubeArchivist instance to manage and analyze video content.

**Purpose:** This script provides functionalities to retrieve the latest downloaded videos, fetch channel and video statistics, search for videos, and retrieve and format task information.

**Usage:**

1.  Set the `TUBE_ARCHIVIST_BASE_URL` and `API_TOKEN` environment variables with your TubeArchivist base URL and API token, respectively.
2.  Run the script:

```bash
python tubearchivist.py
```

**Dependencies:**

*   `requests`
*   `json`
*   `os`
*   `time`
*   `dotenv`

**Configuration:**

The script relies on environment variables for configuration:

*   `TUBE_ARCHIVIST_BASE_URL`: The base URL of your TubeArchivist instance (e.g., `http://tubearchivist.lan`).
*   `API_TOKEN`: Your TubeArchivist API token.

**Note:** Ensure that your TubeArchivist instance is running and accessible. The script includes a retry mechanism for API requests to handle potential server errors.

## Document Management

These scripts interact with document management systems.

### `paperless.py`

**Description:** Interacts with a Paperless instance to manage and analyze documents.

**Purpose:** This script provides functionalities to retrieve a list of documents, retrieve a specific document by ID, create a new document, search for documents, and retrieve the full information for a specific document by ID.

**Usage:**

1.  Set the `PAPERLESS_BASE_URL` and `PAPERLESS_API_TOKEN` environment variables with your Paperless base URL and API token, respectively.
2.  Run the script:

```bash
python paperless.py
```

**Dependencies:**

*   `requests`
*   `json`
*   `os`
*   `dotenv`
*   `openai`
*   `httpx`

**Configuration:**

The script relies on environment variables for configuration:

*   `PAPERLESS_BASE_URL`: The base URL of your Paperless instance (e.g., `http://paperless.lan`).
*   `PAPERLESS_API_TOKEN`: Your Paperless API token.
*   `LLM_BASE_URL`: The base URL of your local LLM server (e.g., `http://localhost:9090/v1`).

**Note:** Ensure that your Paperless instance is running and accessible. This script also requires a local LLM server to be running for document summarization.

## Task Management

These scripts interact with task management systems.

### `taskwarrior.py`

**Description:** Interacts with Taskwarrior to manage tasks using natural language and LLMs.

**Purpose:** This script provides functionalities to add tasks using natural language input, converting it to Taskwarrior commands, get instructions for the most urgent task, and display the most urgent task.

**Usage:**

```bash
python taskwarrior.py [command] [arguments]
```

**Commands:**

*   `generate <natural_language_request>`: Generates a Taskwarrior command from a natural language request.
    Example: `python taskwarrior.py generate "Add a task to buy milk tomorrow"`
*   `urgent`: Displays instructions for the most urgent task.
    Example: `python taskwarrior.py urgent`
*   `get_most_urgent_task_info`: Retrieves and displays information about the most urgent task.
    Example: `python taskwarrior.py get_most_urgent_task_info`
*   (No arguments): Displays the most urgent task and instructions for it.
    Example: `python taskwarrior.py`

**Dependencies:**

*   `subprocess`
*   `json`
*   `sys`
*   `openai`
*   `httpx`
*   `os`
*   `datetime`

**Configuration:**

*   Ensure that Taskwarrior is installed and accessible in your system's PATH.
*   A local LLM server is required for natural language processing.

**Note:** The script uses a local LLM server to generate Taskwarrior commands from natural language input. The quality of the generated commands depends on the capabilities of the LLM you are using. The `taskwarrior.md` file (located at `/usr/local/share/man/taskwarrior.md` by default) provides detailed information about Taskwarrior commands and attributes.

## Web Scraping

These scripts scrape data from websites.

### `llm_rottentomatoes.py`

**Description:** Scrapes movie information from Rotten Tomatoes.

**Purpose:** This script retrieves movie data, including titles, critic ratings, audience ratings, and descriptions, from the Rotten Tomatoes website.

**Usage:**

```bash
python llm_rottentomatoes.py
```

**Dependencies:**

*   `requests`
*   `bs4`
*   `json`

**Note:** This script scrapes data from the Rotten Tomatoes website, so its functionality may be affected by changes to the website's structure.

### `llm-rottentomatoes.bash`

**Description:** Scrapes movie information from Rotten Tomatoes.

**Purpose:** This script retrieves movie data, including titles, critic ratings, audience ratings, and descriptions, from the Rotten Tomatoes website.

**Usage:**

```bash
./llm-rottentomatoes.bash
```

**Dependencies:**

*   `curl`
*   `jq`

## Utilities

These scripts provide useful utility functions.

### `stepper.py`

**Description:** Guides a user through steps to manage a panic attack, using an LLM to validate completion of each step.

**Purpose:** This script provides a set of steps to help a user manage a panic attack. It uses an LLM to determine if the user has completed each step correctly before proceeding to the next step.

**Usage:**

```bash
python stepper.py
```

**Dependencies:**

*   `openai`
*   `httpx`
*   `ast`

**Configuration:**

The script relies on environment variables for configuration:

*   `OPENAI_BASE_URL`: The base URL of your local LLM server (e.g., `http://localhost:9090/v1`).

**Note:** This script requires a local LLM server to be running and accessible. The effectiveness of the script depends on the capabilities of the LLM you are using.

### `llm-weather.bash`

**Description:** Fetches weather information and uses an LLM to generate a weather report.

**Purpose:** This script retrieves weather data for a specified ZIP code from the National Weather Service and uses a local LLM to generate a concise and friendly weather report.

**Usage:**

1.  Set the `zip` variable in the script to your desired ZIP code.
2.  Run the script:

```bash
./llm-weather.bash
```

**Dependencies:**

*   `curl`
*   `jq`
*   `bc`

**Configuration:**

*   Ensure that a local LLM server is running and accessible. The script is configured to connect to a server at `http://localhost:9090/v1`.
*   The script uses `curl` to fetch data from the National Weather Service and `jq` to parse the JSON responses.

**Note:** The script attempts to automatically determine the ZIP code based on your IP address if the `zip` variable is not set manually. The quality of the weather report depends on the capabilities of the LLM you are using.
