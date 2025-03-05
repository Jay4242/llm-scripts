# llm-scripts

A collection of scripts that leverage Large Language Models (LLMs) for various tasks.

## Scripts

-   [llm-conv.py](#llm-convpy) - A script for conducting interactive conversations with an LLM.
-   [llm-file-conv.py](#llm-file-convpy) - Extends `llm-conv.py` by incorporating a file's content into the LLM's context.
-   [llm-file-conv-pygame.py](#llm-file-conv-pygamepy) - Combines the functionality of `llm-file-conv.py` with a Pygame interface.
-   [llm-conv-file-memory.py](#llm-conv-file-memorypy) - Implements a memory mechanism for LLM conversations by updating a text file.
-   [llm-plex.bash](#llm-plexbash) - Interacts with a local Plex media server to provide movie suggestions.
-   [paperless.py](#paperlesspy) - Interacts with a Paperless instance to manage and analyze documents.
-   [tubearchivist.py](#tubearchivistpy) - Interacts with a TubeArchivist instance to manage and analyze video content.
-   [llm-rottentomatoes.bash](#llm-rottentomatoesbash) - Scrapes movie information from Rotten Tomatoes.

These scripts are designed to interact with a local LLM server, such as llama-server, providing functionalities ranging from simple conversations to complex data processing and automation.

## Scripts

### `llm-conv.py`

A Python script for conducting interactive conversations with an LLM.

**Purpose:**
This script takes a system prompt, an initial user prompt, and a temperature value as input. It then initiates a chat session with the LLM, allowing you to have a continuous conversation.

**Usage:**
```bash
python llm-conv.py <system_prompt> <initial_prompt> <temperature>
```
- `<system_prompt>`: A string that sets the context and behavior of the LLM (e.g., "You are a helpful assistant").
- `<initial_prompt>`: The first message you send to the LLM to start the conversation.
- `<temperature>`: A float value (e.g., 0.7) that controls the randomness of the LLM's responses. Higher values result in more creative and unpredictable outputs.

**Note:**
This script does not have built-in context length management. Over time, as the conversation grows, it may exceed the LLM's context window, leading to truncated or nonsensical responses.

### `llm-file-conv.py`

A Python script that extends `llm-conv.py` by incorporating a file's content into the LLM's context.

**Purpose:**
This script allows you to provide the LLM with the content of a file, enabling it to answer questions or perform tasks related to that content.

**Usage:**
```bash
python llm-file-conv.py <system_prompt> <file_path> <initial_prompt> <temperature>
```
- `<system_prompt>`: Same as in `llm-conv.py`.
- `<file_path>`: The path to the file whose content you want to include in the conversation.
- `<initial_prompt>`: Same as in `llm-conv.py`.
- `<temperature>`: Same as in `llm-conv.py`.

**Example:**
```bash
python llm-file-conv.py "You are a code reviewer" my_code.py "What potential bugs do you see in this code?" 0.6
```

### `llm-file-conv-pygame.py`

An experimental script that combines the functionality of `llm-file-conv.py` with a Pygame interface.

**Purpose:**
This script aims to display the conversation with the LLM in a graphical window using Pygame.

**Usage:**
```bash
python llm-file-conv-pygame.py <system_prompt> <file_path> <subject_line> <initial_prompt> <temperature>
```
- `<system_prompt>`: Same as in `llm-file-conv.py`.
- `<file_path>`: Same as in `llm-file-conv.py`.
- `<subject line>`: A short description of the file's content.
- `<initial_prompt>`: Same as in `llm-conv.py`.
- `<temperature>`: Same as in `llm-conv.py`.

**Note:**
The Pygame display functionality is currently incomplete and may not render the text correctly.

### `llm-conv-file-memory.py`

A Python script that attempts to implement a memory mechanism for LLM conversations by updating a text file with relevant information from the conversation.

**Purpose:**
This script aims to maintain a persistent memory of the conversation by allowing the LLM to suggest updates to a "memory" file.

**Usage:**
```bash
python llm-conv-file-memory.py <system_prompt> <file_path> <initial_prompt> <temperature>
```
- `<system_prompt>`: Same as in `llm-file-conv.py`.
- `<file_path>`: The path to the memory file.
- `<initial_prompt>`: Same as in `llm-conv.py`.
- `<temperature>`: Same as in `llm-conv.py`.

**How it works:**
1.  The script reads the content of the memory file.
2.  It sends the file content, along with the user's input, to the LLM.
3.  The LLM determines if the user's input contains information that should be added to the memory file.
4.  If the LLM decides to update the memory file, it suggests the changes.
5.  The script appends the suggested changes to the memory file.

### `llm-plex.bash`

A Bash script that interacts with a local Plex media server to provide movie suggestions based on your library and Rotten Tomatoes data.

**Purpose:**
This script automates the process of getting movie recommendations by:

1.  Fetching movie genres and unwatched movies from your Plex server.
2.  Scraping movie data from Rotten Tomatoes.
3.  Using an LLM to suggest movies based on your Plex library and Rotten Tomatoes ratings.

**Usage:**

1.  Set the `api` variable in the script to your Plex API key.
2.  Ensure that the `PLEX_URL` variable is set correctly (default: `http://plex.lan`).
3.  Run the script:
    ```bash
    ./llm-plex.bash
    ```

**Dependencies:**

-   `curl`
-   `jq`
-   `xmlstarlet`
-   `llm-python-file.py`
-   `llm-python-file-2.py`
-   `llm-rottentomatoes.bash`

**Note:**

-   This script requires that you have a local LLM server running and accessible.
-   The script uses several helper scripts (`llm-python-file.py`, `llm-python-file-2.py`, and `llm-rottentomatoes.bash`) to interact with the LLM and scrape data from Rotten Tomatoes.

Screenshot of output:

### `paperless.py`

A Python script that interacts with a Paperless instance to manage and analyze documents.

**Purpose:**

This script provides functionalities to:

-   Retrieve a list of documents.
-   Retrieve a specific document by ID.
-   Create a new document.
-   Search for documents.
-   Retrieve the full information for a specific document by ID.

**Usage:**

1.  Set the `PAPERLESS_BASE_URL` and `PAPERLESS_API_TOKEN` environment variables with your Paperless base URL and API token, respectively.
2.  Run the script:

```bash
python paperless.py
```

**Dependencies:**

-   `requests`
-   `json`
-   `os`
-   `dotenv`
-   `openai`
-   `httpx`

**Configuration:**

The script relies on environment variables for configuration:

-   `PAPERLESS_BASE_URL`: The base URL of your Paperless instance (e.g., `http://paperless.lan`).
-   `PAPERLESS_API_TOKEN`: Your Paperless API token.
-   `LLM_BASE_URL`: The base URL of your local LLM server (e.g., `http://localhost:9090/v1`).

**Note:**

-   Ensure that your Paperless instance is running and accessible.
-   This script also requires a local LLM server to be running for document summarization.

### `llm-rottentomatoes.bash`

A Bash script that scrapes movie information from Rotten Tomatoes.

**Purpose:**

This script retrieves movie data, including titles, critic ratings, audience ratings, and descriptions, from the Rotten Tomatoes website.

**Usage:**

```bash
./llm-rottentomatoes.bash
```

**Dependencies:**

-   `curl`
-   `jq`

### `tubearchivist.py`

A Python script that interacts with a TubeArchivist instance to manage and analyze video content.

**Purpose:**

This script provides functionalities to:

-   Retrieve the latest downloaded videos.
-   Fetch channel and video statistics.
-   Search for videos.
-   Retrieve and format task information.

**Usage:**

1.  Set the `TUBE_ARCHIVIST_BASE_URL` and `API_TOKEN` environment variables with your TubeArchivist base URL and API token, respectively.
2.  Run the script:

```bash
python tubearchivist.py
```

**Dependencies:**

-   `requests`
-   `json`
-   `os`
-   `time`
-   `dotenv`

**Configuration:**

The script relies on environment variables for configuration:

-   `TUBE_ARCHIVIST_BASE_URL`: The base URL of your TubeArchivist instance (e.g., `http://tubearchivist.lan`).
-   `API_TOKEN`: Your TubeArchivist API token.

**Note:**

-   Ensure that your TubeArchivist instance is running and accessible.
-   The script includes a retry mechanism for API requests to handle potential server errors.
