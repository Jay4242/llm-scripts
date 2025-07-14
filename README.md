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

*   [LLM Servers](#llm-servers)
*   [Conversational AI](#conversational-ai)
*   [File Processing](#file-processing)
*   [Media Management](#media-management)
*   [Document Management](#document-management)
*   [Task Management](#task-management)
*   [Web Scraping](#web-scraping)
*   [Humor](#humor)
*   [Diagram Generation](#diagram-generation)
*   [Vision AI](#vision-ai)
*   [Utilities](#utilities)

## LLM Servers

These scripts provide local LLM server functionalities.

<details>
<summary>llama-gemma3-server.py</summary>

### `llama-gemma3-server.py`

**Description:** A Flask-based web server that provides an OpenAI-compatible API endpoint (`/v1/chat/completions`) for interacting with a local `llama-gemma3-cli` executable. It supports both text and image (vision) inputs.

**Purpose:** This script allows users to run a local Gemma 3B model with vision capabilities via a web API, making it compatible with applications designed to use OpenAI's chat completion API. It handles temporary file creation for images and manages the `llama-gemma3-cli` process.

**Usage:**

1.  **Configuration:**
    *   Set the `MODEL_DIR` variable in the script to the absolute path of the directory containing your `google_gemma-3-4b-it-Q8_0.gguf` and `mmproj-google-gemma-3-4b-it-f32.gguf` model files.
    *   Ensure `llama-gemma3-cli` executable is in `/usr/local/bin` or update the `command` variable in the script to its correct path.
2.  **Run the server:**

    ```bash
    python llama-gemma3-server.py
    ```

    The server will run on `http://0.0.0.0:5000` by default.

**Dependencies:**

*   `flask`
*   `llama-gemma3-cli` (external executable)

**Configuration:**

*   `MODEL_DIR`: **MUST BE SET** by the user to the directory containing the Gemma model files.
*   `MODEL_FILE`: `google_gemma-3-4b-it-Q8_0.gguf` (default)
*   `MMPROJ_FILE`: `mmproj-google-gemma-3-4b-it-f32.gguf` (default)
*   **Port:** Hardcoded to `5000` in `get_port()` function.

**Note:** The script creates temporary directories and copies model files to them on startup. It handles base64 encoded image data from the API request and saves them as temporary files for `llama-gemma3-cli`. Temporary image files are cleaned up after each request. The output from `llama-gemma3-cli` is filtered to remove initial log lines.
</details>

## Conversational AI

These scripts provide different ways to interact with LLMs in a conversational manner.

<details>
<summary>llm-conv.py</summary>

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
</details>

<details>
<summary>llm-file-conv.py</summary>

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
</details>

<details>
<summary>llm-file-conv-pygame.py</summary>

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
</details>

<details>
<summary>llm-conv-file-memory.py</summary>

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
</details>

## File Processing

These scripts process files using LLMs.

<details>
<summary>grammarai.py</summary>

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

*   Ensure that a local LLM server is running and accessible. The script connects to the LLM server specified by the `OPENAI_BASE_URL` environment variable (e.g., `http://localhost:9090/v1`).

**Note:** The quality of the grammar correction depends on the capabilities of the LLM you are using.
</details>

<details>
<summary>llm-python-file.py</summary>

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
</details>

<details>
<summary>llm-python-file-2.py</summary>

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
</details>

<details>
<summary>llm-srt.py</summary>

### `llm-srt.py`

**Description:** Translates an SRT (SubRip Subtitle) file using an LLM.

**Purpose:** This script reads an SRT file, extracts the subtitle text, translates it to a specified target language using a local LLM, and then saves the translated content to a new SRT file.

**Usage:**

```bash
python llm-srt.py <input_srt_file> <output_srt_file> [<target_language>]
```

*   `<input_srt_file>`: The path to the original SRT file to be translated.
*   `<output_srt_file>`: The path where the translated SRT file will be saved.
*   `[<target_language>]`: Optional. The language to translate the subtitles to (e.g., "Spanish", "German"). Defaults to "French" if not provided.

**Dependencies:**

*   `openai`
*   `httpx`
*   `sys`
*   `re`

**Configuration:**

*   Ensure that a local LLM server is running and accessible. The script is configured to connect to a server at `http://localhost:9090/v1`.
*   The `model` used in the script is `gemma-3-4b-it-q8_0`. You may need to adjust this based on the models available on your local LLM server.

**Example:**

```bash
python llm-srt.py original.srt translated_spanish.srt Spanish
```

**Note:** The quality of the translation depends on the capabilities of the LLM you are using.
</details>

<details>
<summary>llm-pdf.py</summary>

### `llm-pdf.py`

**Description:** Downloads a PDF from a given URL, extracts its text content, and sends it to an LLM for analysis.

**Purpose:** This script allows you to process the content of a PDF document using an LLM, enabling tasks like summarization, question answering, or extracting key information from scientific papers or other PDF-based documents.

**Usage:**

```bash
python llm-pdf.py <pdf_url>
```

*   `<pdf_url>`: The URL of the PDF document to be downloaded and processed.

**Dependencies:**

*   `requests`
*   `pdfminer.six`
*   `openai`
*   `httpx`

**Configuration:**

*   Ensure that a local LLM server is running and accessible. The script is configured to connect to a server at `http://localhost:9090/v1`.
*   The `model` used in the script is `gemma-3-4b-it-q8_0`. You may need to adjust this based on the models available on your local LLM server.
*   The `system_prompt`, `pre_prompt`, and `post_prompt` are hardcoded within the script and can be modified to suit different analysis tasks.

**Example:**

```bash
python llm-pdf.py "https://arxiv.org/pdf/2307.09288.pdf"
```

**Note:** The quality of the LLM's analysis depends on the clarity of the extracted text and the capabilities of the LLM you are using.
</details>

<details>
<summary>llm-python-file-embedding-by-line.py</summary>

### `llm-python-file-embedding-by-line.py`

**Description:** Generates embeddings for each line of a given text file using an LLM.

**Purpose:** This script reads a text file line by line, cleans each line, and then sends it to a local LLM server to generate a text embedding. The output includes the file path, the processed line, and its embedding, formatted as a CSV-like string.

**Usage:**

```bash
python llm-python-file-embedding-by-line.py <document_file_path>
```

*   `<document_file_path>`: The path to the text file whose lines will be embedded.

**Dependencies:**

*   `openai`

**Configuration:**

*   Ensure that a local LLM server capable of generating embeddings is running and accessible. The script is configured to connect to a server at `http://localhost:9090/v1`.
*   The `model` used for embeddings is hardcoded to `"nomic-embed-text-v1.5.q8_0"`. You may need to adjust this based on the models available on your local LLM server.

**Note:** Each line is stripped of leading/trailing whitespace, converted to lowercase, and has double quotes, asterisks, and single quotes removed before embedding. Empty lines are skipped.
</details>

<details>
<summary>llm-python-search-embeddings.py</summary>

### `llm-python-search-embeddings.py`

**Description:** Searches for relevant text entries in a CSV file based on a search phrase using LLM embeddings and cosine similarity.

**Purpose:** This script allows you to find the most semantically similar text entries within a pre-computed CSV of text and their embeddings, given a new search phrase. It's useful for semantic search, content recommendation, or finding related information in a dataset.

**Usage:**

```bash
python llm-python-search-embeddings.py <csv_filename> "<search_phrase>" <top_n>
```

*   `<csv_filename>`: The path to the CSV file containing text and their embeddings (e.g., `embeddings.csv`). The CSV is expected to have text in the first column and their corresponding embeddings (as a string representation of a list) in the second column.
*   `<search_phrase>`: The text phrase to search for (e.g., `"What is the capital of France?"`). Enclose in double quotes if it contains spaces.
*   `<top_n>`: The number of top relevant results to return (e.g., `5`).

**Dependencies:**

*   `openai`
*   `pandas`
*   `numpy`
*   `scikit-learn` (for `cosine_similarity`)

**Configuration:**

*   Ensure that a local LLM server capable of generating embeddings is running and accessible. The script is configured to connect to a server at `http://localhost:9090/v1`.
*   The `model` used for embeddings is hardcoded to `"nomic-embed-text-v1.5.q8_0"`. You may need to adjust this based on the models available on your local LLM server.

**Example:**

```bash
python llm-python-search-embeddings.py my_documents_embeddings.csv "machine learning applications" 3
```

**Note:** The quality of the search results depends on the quality of the embeddings and the capabilities of the LLM used for generating them.
</details>

## Media Management

These scripts interact with media server applications.

<details>
<summary>llm_plex.py</summary>

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

The script uses the following default values, which can be modified directly in the script:

*   `PLEX_URL`: The base URL of your Plex server (default: `http://plex.lan`).
*   `PLEX_LIBRARY_SECTION`: The library section ID for movies (default: `"1"`).
*   `LLM_BASE_URL`: The base URL of your local LLM server (default: `http://localhost:9090/v1`).
*   `LLM_MODEL`: The name of the LLM model to use (default: `"llama-3.2-3b-it-q8_0"`).
*   `DEFAULT_TEMPERATURE`: The default temperature for LLM queries (default: `0.7`).
*   `ROTTEN_TOMATOES_URL`: The URL for scraping Rotten Tomatoes data (default: `"https://www.rottentomatoes.com/browse/movies_at_home/sort:popular"`).

The `PLEX_API_KEY` is read from the environment variable `PLEX_API_KEY`.

**Note:** This script requires that you have a local LLM server running and accessible and uses `llm_rottentomatoes.py` to scrape data from Rotten Tomatoes.
</details>

<details>
<summary>llm-plex.bash</summary>

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
</details>

<details>
<summary>tubearchivist.py</summary>

### `tubearchivist.py`

**Description:** Interacts with a TubeArchivist instance to manage and analyze video content.

**Purpose:** This script provides comprehensive functionalities to interact with a TubeArchivist instance, including retrieving the latest downloaded videos, managing the download queue, fetching channel and video details (including comments and similar videos), searching for videos and channels, retrieving user configuration, and accessing task information.

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
</details>

## YouTube Tools

These scripts provide tools for interacting with YouTube.

<details>
<summary>llm-channel-search.bash</summary>

### `llm-channel-search.bash`

**Description:** Searches a YouTube channel for videos containing a specific query in their subtitles and uses an LLM to determine if the video content helps answer the question.

**Purpose:** This script automates the process of searching YouTube channel video transcripts for a specific query and then leveraging an LLM to assess the relevance of the video's content to a given question or topic.

**Usage:**

```bash
./llm-channel-search.bash
```

The script will prompt you for:
*   `What channel URL? (/videos)`: The YouTube channel URL (e.g., `https://www.youtube.com/channel/CHANNEL_ID/videos`).
*   `What are you looking for?`: The question or topic you want the LLM to answer based on the video transcripts.

**Dependencies:**

*   `yt-dlp` (external executable)
*   `jq` (external executable)
*   `html2text` (external executable)
*   `llm-python-file.py` (for LLM interaction)

**Configuration:**

*   Requires `yt-dlp`, `jq`, and `html2text` to be installed and accessible in your system's PATH.
*   Requires `llm-python-file.py` to be accessible and configured to connect to a local LLM server.
*   Temporary files are stored in `/dev/shm/llm-channel-search/`.

**Note:** The script processes videos one by one and outputs "Yes" if the LLM determines the video content is relevant to the question, along with the LLM's explanation.

</details>

<details>
<summary>llm-channel-search.py</summary>

### `llm-channel-search.py`

**Description:** Searches a YouTube channel for videos containing a specific query in their subtitles. It can also send matching subtitle content to an LLM for further analysis.

**Purpose:** To find specific content within a YouTube channel by searching through video subtitles and optionally leverage an LLM to answer questions about the matching content.

**Usage:**

```bash
python llm-channel-search.py <channel_url> <search_query> [--llm <llm_question>] [--download_vtt]
```

*   `<channel_url>`: The YouTube channel URL (e.g., `/channel/CHANNEL_ID` or `/user/USERNAME`).
*   `<search_query>`: The text to search for within the video subtitles.
*   `--llm <llm_question>`: Optional. A question or command to send to the LLM along with the matching subtitles for further analysis.
*   `--download_vtt`: Optional. Downloads VTT subtitles for the first video found in the channel and exits.

**Dependencies:**

*   `yt-dlp`
*   `html2text`
*   `openai` (indirectly via `llm-python-file.py`)
*   `httpx` (indirectly via `llm-python-file.py`)

**Configuration:**

*   Requires `llm-python-file.py` to be accessible at `/usr/local/bin/llm-python-file.py` (or adjust the path in the script).
*   Requires a local LLM server to be running and accessible for the `--llm` functionality.
</details>

<details>
<summary>llm-fm.py</summary>

### `llm-fm.py`

**Description:** A radio DJ powered by a language model that plays music from YouTube and provides weather reports.

**Purpose:** This script acts as an AI-powered radio station. It uses an LLM to select songs and generate descriptions, plays them via `yt-dlp` and `mpv`, and periodically provides weather updates based on a specified ZIP code.

**Usage:**

```bash
python llm-fm.py [genre]
```

*   `[genre]`: Optional. The genre of music for the radio station (default: "Pop").

**Dependencies:**

*   `requests`
*   `pyttsx3`
*   `yt-dlp` (external executable)
*   `mpv` (external executable)
*   `python-dotenv`
*   `pyttsx3`
*   `subprocess`
*   `re`
*   `argparse`
*   `datetime`
*   `logging`
*   `socket`

**Configuration:**

*   `ZIP_CODE`: **MUST BE SET** as an environment variable (e.g., in a `.env` file) for weather reports.
*   `BASE_URL`: **MUST BE SET** as an environment variable to the URL of your local LLM server (e.g., `http://localhost:9090/v1`).
*   `MODEL`: The LLM model to use (default: `gemma-3-4b-it-q8_0`).
*   `ESPEAK_SPEED`: Speech rate for announcements (default: `160`).
*   `MPV_SOCKET`: IPC socket for `mpv` (default: `/dev/shm/mpv_socket`).

**Notes:**

*   Requires a local LLM server with chat completion capabilities.
*   Requires `yt-dlp` and `mpv` to be installed and accessible in your system's PATH for audio playback.
*   Uses Nominatim for ZIP code to latitude/longitude conversion and National Weather Service API for weather data.
*   The script maintains a list of recently played songs to avoid repetition.
*   It includes signal handlers for graceful exit (Ctrl+C).
</details>

## Document Management

These scripts interact with document management systems.

<details>
<summary>paperless.py</summary>

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
</details>

<details>
<summary>llm-document-sort.py</summary>

### `llm-document-sort.py`

**Description:** Sorts documents into predefined categories using an LLM.

**Purpose:** This script reads documents from an 'unsorted' directory, uses an LLM to determine which subdirectory within a 'sorted' directory each document belongs to, and then copies the document to the chosen category subdirectory.

**Usage:**

```bash
python llm-document-sort.py
```

**Dependencies:**

*   `openai`
*   `httpx`
*   `shutil`

**Configuration:**

*   Requires two directories in the same location as the script: `unsorted` (for documents to be sorted) and `sorted` (containing subdirectories representing categories).
*   Ensure a local LLM server with vision capabilities is running and accessible. The script is configured to connect to a server at `http://localhost:9090/v1`.
*   The `model` used in the script is `gemma-3-4b-it-q8_0`. You may need to adjust this based on the models available on your local LLM server.

**Note:** The LLM's ability to correctly categorize documents depends on its training and the clarity of the document content.
</details>

## Task Management

These scripts interact with task management systems.

<details>
<summary>taskwarrior.py</summary>

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
</details>

## Web Scraping

These scripts scrape data from websites.

<details>
<summary>llm_rottentomatoes.py</summary>

### `llm_rottentomatoes.py`

**Description:** Scrapes movie information from Rotten Tomatoes.

**Purpose:** This script retrieves comprehensive movie data from the Rotten Tomatoes website, including titles, critic ratings, audience ratings, streaming dates, movie URLs, descriptions, genres, content ratings, actors, and directors.

**Usage:**

```bash
python llm_rottentomatoes.py
```

**Dependencies:**

*   `requests`
*   `bs4`
*   `json`

**Note:** This script scrapes data from the Rotten Tomatoes website, so its functionality may be affected by changes to the website's structure.
</details>

<details>
<summary>llm-rottentomatoes.bash</summary>

### `llm-rottentomatoes.bash`

**Description:** Scrapes movie information from Rotten Tomatoes.

**Purpose:** This script retrieves comprehensive movie data from the Rotten Tomatoes website, including titles, critic ratings, audience ratings, critic sentiment, audience sentiment, directors, actors, and descriptions.

**Usage:**

```bash
./llm-rottentomatoes.bash
```

**Dependencies:**

*   `curl`
*   `jq`

</details>

<details>
<summary>fark.py</summary>

### `fark.py`

**Description:** Fetches and parses headlines from Fark.com.

**Purpose:** This script scrapes the latest headlines from Fark.com, including their associated URLs and tags. It can also shuffle the output and resolve redirect URLs.

**Usage:**

```bash
python fark.py [--shuffle] [--resolve <url>]
```

*   `--shuffle`: Optional. Shuffles the order of the output headlines.
*   `--resolve <url>`: Optional. Resolves a given Fark.com redirect URL to its final destination.

**Dependencies:**

*   `requests`
*   `bs4`

**Example:**

```bash
python fark.py
python fark.py --shuffle
python fark.py --resolve "https://www.fark.com/go/1234567"
```

**Note:** This script scrapes data from Fark.com, so its functionality may be affected by changes to the website's structure.
</details>

<details>
<summary>sales_history.py</summary>

### `sales_history.py`

**Description:** Scrapes sold item history from eBay.

**Purpose:** This script fetches data from eBay's sold listings for a given search term, extracting details such as item title, sold date, selling price, delivery price, item URL, and image URL.

**Usage:**

```bash
python sales_history.py "<search_term>"
```

*   `<search_term>`: The product or item you want to search for on eBay (e.g., "vintage camera", "iphone 12").

**Dependencies:**

*   `requests`
*   `bs4` (BeautifulSoup4)
*   `json`
*   `re`
*   `sys`
*   `urllib.parse`

**Example:**

```bash
python sales_history.py "Nintendo Switch"
```

**Note:** This script scrapes data from eBay, so its functionality may be affected by changes to eBay's website structure. It uses a mobile user-agent to fetch the page content.
</details>

<details>
<summary>llm-website-summary.bash</summary>

### `llm-website-summary.bash`

**Description:** Fetches the content of a given URL and uses an LLM to summarize or extract information from it.

**Purpose:** This script takes a URL as input, downloads its content using `lynx`, and then allows the user to interactively ask an LLM questions or provide tasks related to the website's content.

**Usage:**

```bash
./llm-website-summary.bash <url>
```

*   `<url>`: The URL of the website to process.

**Dependencies:**

*   `lynx` (command-line web browser)
*   `llm-python-file.py` (for LLM interaction)

**Configuration:**

*   Ensure `lynx` is installed and accessible in your system's PATH.
*   Ensure `llm-python-file.py` is accessible in your system's PATH and configured to connect to a local LLM server.
</details>

## Video Analysis

These scripts analyze video content using LLMs.

<details>
<summary>how_its_made.bash</summary>

### `how_its_made.bash`

**Description:** Analyzes a video file by detecting scenes, extracting keyframes, and generating humorous descriptions in the style of "How It's Made" using an LLM with vision capabilities.

**Purpose:** This script automates the process of breaking down a video into its constituent scenes, generating visual summaries, and then using an LLM to create entertaining and concise descriptions for each scene, mimicking the popular documentary style.

**Usage:**

```bash
./how_its_made.bash <video_file> <output_directory>
```

*   `<video_file>`: The path to the input video file (e.g., `my_video.mp4`).
*   `<output_directory>`: The directory where scene images and the generated descriptions will be saved.

**Dependencies:**

*   `ffmpeg` (external executable, for scene detection and keyframe extraction)
*   `llm-python-vision.py` (for LLM interaction with images)

**Configuration:**

*   Requires `ffmpeg` to be installed and accessible in your system's PATH.
*   Requires `llm-python-vision.py` to be accessible at `/usr/bin/python3` (or adjust the path in the script) and configured to connect to a local LLM server with vision capabilities.

**Note:** The script processes images in batches of two for LLM analysis. The quality and humor of the descriptions depend on the capabilities of the LLM you are using.
</details>

## Humor

These scripts generate humorous content using LLMs.

<details>
<summary>llm-meme.bash</summary>

### `llm-meme.bash`

**Description:** Generates meme text for an image using an LLM with vision capabilities and then overlays the text on the image.

**Purpose:** This script automates the creation of memes by leveraging an LLM to generate humorous top and bottom text based on an input image.

**Usage:**

```bash
./llm-meme.bash <image_path>
```

*   `<image_path>`: The path to the input image file.

**Dependencies:**

*   `llm-python-vision.py` (for LLM interaction with images)
*   `jq` (external executable, for parsing JSON)
*   `ImageMagick` (`convert`, `identify`) (external executables, for image manipulation)

**Configuration:**

*   Requires `llm-python-vision.py`, `jq`, and `ImageMagick` to be installed and accessible in your system's PATH.
*   The LLM server URL and model are configured within the `llm-python-vision.py` script it calls.
*   The output meme image is saved as `output.jpg` in the current directory.

**Note:** The quality and humor of the generated meme text depend on the capabilities of the LLM you are using.
</details>

<details>
<summary>llm-roast.py</summary>

### `llm-roast.py`

**Description:** Scrapes a public figure's biography from `famousbirthdays.com` and generates a humorous roast using an LLM.

**Purpose:** To create a personalized, witty roast based on publicly available information about a person.

**Usage:**

```bash
python llm-roast.py <famousbirthdays.com_URL>
```

*   `<famousbirthdays.com_URL>`: The URL of the public figure's page on `famousbirthdays.com`.

**Dependencies:**

*   `requests`
*   `bs4` (BeautifulSoup4)
*   `re`
*   `sys`
*   `openai`
*   `httpx`

**Configuration:**

*   Requires a local LLM server running and accessible at `http://localhost:9090/v1`.
*   The default model used is `gemma-3-4b-it-q8_0`. You may need to adjust this based on the models available on your local LLM server.

**Note:** The quality of the roast depends on the capabilities of the LLM you are using and the information available on the `famousbirthdays.com` page.
</details>

## Diagram Generation

These scripts generate diagrams using LLMs.

<details>
<summary>llm-mermaid.py</summary>

### `llm-mermaid.py`

**Description:** Generates Mermaid.js diagrams from natural language prompts using an LLM and displays them in a web browser.

**Purpose:** This script allows users to create flowcharts, sequence diagrams, gantt charts, and other diagrams by simply describing them in natural language. The LLM converts the description into Mermaid.js code, which is then rendered in a local HTML page and opened in the default web browser.

**Usage:**

```bash
python llm-mermaid.py "<user_prompt>"
```

*   `<user_prompt>`: A natural language description of the diagram you want to generate (e.g., "A flowchart showing user login process: Start -> Enter Username/Password -> Validate Credentials -> If valid, Go to Dashboard; Else, Show Error and retry.").

**Dependencies:**

*   `openai`
*   `webbrowser`
*   `base64`

**Configuration:**

*   Ensure that a local LLM server is running and accessible. The script is configured to connect to a server at `http://localhost:9090/v1`.
*   The `model` used in the script is `gemma-3-4b-it-q8_0`. You may need to adjust this based on the models available on your local LLM server.

**Note:** The script generates an HTML file with the Mermaid.js code and opens it as a data URI in your default web browser. An internet connection is required to load the Mermaid.js library from `cdn.jsdelivr.net`.
</details>

## Vision AI

These scripts leverage LLMs with vision capabilities.

<details>
<summary>llm-web-vision.py</summary>

### `llm-web-vision.py`

**Description:** Analyzes an image from a specified path using an LLM with vision capabilities.

**Purpose:** This script takes an image file path and a text prompt as input, encodes the image to base64, and sends both to a local LLM server for analysis. The LLM then provides a response based on the image and the prompt.

**Usage:**

```bash
python llm-web-vision.py <image_path> <text_prompt>
```

*   `<image_path>`: The absolute or relative path to the image file (e.g., `image.jpg`, `/home/user/pictures/photo.png`).
*   `<text_prompt>`: The text prompt or question you want to ask the LLM about the image (e.g., "Describe this image", "What is happening here?").

**Dependencies:**

*   `openai`
*   `httpx`

**Configuration:**

*   Ensure that a local LLM server with vision capabilities is running and accessible. The script is configured to connect to a server at `http://localhost:9090/v1`.
*   The `model` used in the script is `gemma-3-4b-it-q8_0`. You may need to adjust this based on the models available on your local LLM server.

**Example:**

```bash
python llm-web-vision.py my_image.jpg "What is the main subject of this image?"
```

**Note:** The script expects the image to be in a format supported by the LLM (e.g., JPEG).
</details>

<details>
<summary>llm-python-vision-ollama.py</summary>

### `llm-python-vision-ollama.py`

**Description:** Analyzes an image from a specified path using a local Ollama LLM with vision capabilities.

**Purpose:** This script takes an image file path and a text prompt as input, encodes the image to base64, and sends both to a local Ollama LLM server for analysis. The LLM then provides a response based on the image and the prompt.

**Usage:**

```bash
python llm-python-vision-ollama.py "<text_prompt>" <image_path>
```

*   `<text_prompt>`: The text prompt or question you want to ask the LLM about the image (e.g., "Describe this image", "What is happening here?").
*   `<image_path>`: The absolute or relative path to the image file (e.g., `image.jpg`, `/home/anon/pictures/photo.png`).

**Dependencies:**

*   `openai`
*   `requests`

**Configuration:**

*   Ensure that a local Ollama LLM server with vision capabilities is running and accessible. The script is configured to connect to a server at `http://localhost:11434/v1`.
*   The `model` used in the script is `llama3.2-vision:latest`. You may need to adjust this based on the models available on your local Ollama server.

**Example:**

```bash
python llm-python-vision-ollama.py "What is the main subject of this image?" my_image.jpg
```

**Note:** The script expects the image to be in a format supported by the LLM (e.g., JPEG).
</details>

<details>
<summary>llm-python-vision-multi-images.py</summary>

### `llm-python-vision-multi-images.py`

**Description:** Analyzes multiple images (frames from a video) using an LLM with vision capabilities.

**Purpose:** This script takes a text prompt and multiple image file paths (expected to be video frames with `frame_XXX.jpg` naming) as input, encodes the images to base64, and sends both to a local LLM server for analysis. It also extracts and appends the frame range to the prompt. The LLM then provides a response based on the images and the prompt.

**Usage:**

```bash
python llm-python-vision-multi-images.py "<text_prompt>" <temperature> <image_path_1> [<image_path_2> ...]
```

*   `<text_prompt>`: The text prompt or question you want to ask the LLM about the images (e.g., "Describe what is happening in these frames").
*   `<temperature>`: A float value (e.g., 0.7) that controls the randomness of the LLM's responses.
*   `<image_path_1> [<image_path_2> ...]`: One or more absolute or relative paths to the image files (e.g., `frame_001.jpg`, `/home/anon/video_frames/frame_002.jpg`). Images are expected to be named `frame_XXX.jpg`.

**Dependencies:**

*   `openai`
*   `httpx`
*   `re`

**Configuration:**

*   Ensure that a local LLM server with vision capabilities is running and accessible. The script is configured to connect to a server at `http://localhost:9595/v1`.
*   The `model` used in the script is `gemma3:4b-it-q8_0`. You may need to adjust this based on the models available on your local LLM server.

**Example:**

```bash
python llm-python-vision-multi-images.py "What is the sequence of events in these frames?" 0.5 frame_001.jpg frame_002.jpg frame_003.jpg
```
</details>

<details>
<summary>llm-screenshot.bash</summary>

### `llm-screenshot.bash`

**Description:** Continuously captures screenshots of a selected window and uses an LLM with vision capabilities to describe the content of the screenshots.

**Purpose:** This script automates the process of monitoring a specific window's visual content and generating real-time descriptions using an LLM. It's useful for continuous visual analysis or accessibility purposes.

**Usage:**

```bash
./llm-screenshot.bash
```

**Dependencies:**

*   `xdotool` (external executable, for selecting windows)
*   `scrot` (external executable, for taking screenshots)
*   `llm-python-vision-ollama.py` (for LLM interaction with images)

**Configuration:**

*   Requires `xdotool` and `scrot` to be installed and accessible in your system's PATH.
*   Requires `llm-python-vision-ollama.py` to be accessible at `/usr/local/bin/llm-python-vision-ollama.py` (or adjust the path in the script) and configured to connect to a local Ollama LLM server with vision capabilities.
*   Screenshots are temporarily saved to `/dev/shm/llm-screenshot.png`.
*   The script takes a screenshot and describes it every 60 seconds.

**Note:** The script will prompt you to select a window after execution.
</details>

<details>
<summary>llm-pyboy.py</summary>

### `llm-pyboy.py`

**Description:** Interacts with a PyBoy (Game Boy emulator) instance, captures screenshots, and sends them to an LLM with vision capabilities for analysis.

**Purpose:** This script allows for real-time visual analysis of Game Boy game states by an LLM. It captures the emulator's screen, encodes it as a base64 image, and sends it along with a user-provided text prompt to a local LLM server. The LLM's response is then printed to the console.

**Usage:**

```bash
python llm-pyboy.py <rom_file>
```

**Dependencies:**

*   `pyboy`
*   `Pillow` (PIL)
*   `openai`
*   `httpx`

**Configuration:**

*   Ensure that a local LLM server with vision capabilities is running and accessible. The script is configured to connect to a server at `http://localhost:9090/v1`.
*   The `model` used in the script is `gemma-3-4b-it-q8_0`. You may need to adjust this based on the models available on your local LLM server.
*   The script takes a screenshot and sends it to the LLM after every 1200 game ticks (frames).

**Note:** This script requires a Game Boy ROM file to run. The quality of the LLM's analysis depends on its vision capabilities and the clarity of the game screen.
</details>

<details>
<summary>llm-live-vision.bash</summary>

### `llm-live-vision.bash`

**Description:** Continuously captures a frame from a video URL copied from the clipboard, analyzes it using an LLM with vision capabilities, speaks the description, and displays the image.

**Purpose:** This script automates the process of real-time visual analysis of video content by extracting frames, generating descriptions using an LLM, and providing both visual and auditory feedback. It's useful for live content analysis or accessibility.

**Usage:**

```bash
./llm-live-vision.bash
```

**Dependencies:**

*   `ffmpeg` (external executable)
*   `yt-dlp` (external executable)
*   `xclip` (external executable)
*   `llm-python-vision-ollama.py` (for LLM interaction with images)
*   `ristretto` (external executable, for image display)
*   `espeak` (external executable, for text-to-speech)

**Configuration:**

*   Requires `ffmpeg`, `yt-dlp`, `xclip`, `ristretto`, and `espeak` to be installed and accessible in your system's PATH.
*   Requires `llm-python-vision-ollama.py` to be accessible and configured to connect to a local Ollama LLM server with vision capabilities.
*   Temporary files (`/dev/shm/output.jpg`, `/dev/shm/output.txt`) are used for image and text output.
*   The script continuously loops, processing a new frame every second.

**Note:** The script expects a video URL to be present in the clipboard. The quality of the analysis depends on the capabilities of the LLM you are using.
</details>

## Utilities

These scripts provide useful utility functions.

<details>
<summary>stepper.py</summary>

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
</details>

<details>
<summary>wolframalpha.py</summary>

### `wolframalpha.py`

**Description:** Fetches answers and step-by-step solutions from Wolfram Alpha.

**Purpose:** This script connects to the Wolfram Alpha WebSocket API to retrieve computational knowledge and answers for a given query. It can also display images returned by Wolfram Alpha.

**Usage:**

```bash
python wolframalpha.py "<search_term>"
```

*   `<search_term>`: The query to send to Wolfram Alpha (e.g., "derivative of x^2", "population of california").

**Dependencies:**

*   `websocket-client`
*   `Pillow`
*   `tkinter` (for image display)

**Note:** This script requires an internet connection to access the Wolfram Alpha API. Image display requires `Pillow` and `tkinter` to be installed.
</details>

<details>
<summary>llm-weather.bash</summary>

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
</details>

## Meshtastic Tools

These scripts provide tools for interacting with Meshtastic devices.

<details>
<summary>llm-meshtastic-reader.py</summary>

### `llm-meshtastic-reader.py`

**Description:** Listens for Meshtastic text messages, processes them with an LLM, and sends the LLM's response back to the sender.

**Purpose:** This script acts as an LLM-powered responder for Meshtastic messages. When a message is received by the configured Meshtastic node, it forwards the message to a local LLM, incorporates the current date and time into the system prompt, and then sends the LLM's generated response back to the original sender, splitting long responses into multiple chunks if necessary.

**Usage:**

1.  Ensure your Meshtastic device is connected and accessible (e.g., via USB).
2.  Configure the LLM settings within the script (e.g., `LLM_BASE_URL`, `LLM_MODEL`).
3.  Run the script:

    ```bash
    python llm-meshtastic-reader.py
    ```

**Dependencies:**

*   `meshtastic`
*   `pubsub`
*   `openai`
*   `httpx`

**Configuration:**

The script uses the following variables, which can be modified directly in the script:

*   `LLM_BASE_URL`: The base URL of your local LLM server (default: `http://localhost:9090/v1`).
*   `LLM_API_KEY`: API key for the LLM (default: `"none"`).
*   `LLM_MODEL`: The name of the LLM model to use (default: `"gemma-3-4b-it-q8_0"`).
*   `LLM_SYSTEM_PROMPT`: System prompt for the LLM (default: `"You are a helpful assistant responding to Meshtastic text messages."`).
*   `LLM_PREPROMPT`: Pre-prompt for the LLM (default: `"The user says: "`).
*   `LLM_POSTPROMPT`: Post-prompt for the LLM (default: `"Respond to the user."`).
*   `LLM_TEMPERATURE`: Temperature for LLM queries (default: `0.7`).
*   `LLM_TIMEOUT`: Timeout for LLM requests in seconds (default: `3600`).
*   `MAX_MESSAGE_LENGTH`: Maximum characters per Meshtastic message chunk (default: `200`).

**Note:** This script requires a local LLM server to be running and accessible. It automatically attempts to connect to a Meshtastic device. Ensure the `meshtastic` Python library is correctly installed and your device is recognized by the system.
</details>

<details>
<summary>llm-meshtastic-tools-emb-desc-match.py</summary>

### `llm-meshtastic-tools-emb-desc-match.py`

**Description:** Listens for Meshtastic text messages, uses an LLM to select and execute a tool based on the message content using embedding similarity, and sends the tool's response back to the sender.

**Purpose:** This script acts as an LLM-powered assistant for Meshtastic messages. It dynamically selects the most relevant tool (e.g., system information, weather reports, general chat, or random numbers) by comparing the user's message embedding with the embeddings of predefined tool descriptions.

**Usage:**

1.  Ensure your Meshtastic device is connected and accessible (e.g., via USB).
2.  Configure the LLM settings within the script (e.g., `LLM_BASE_URL`, `EMBEDDING_BASE_URL`, `LLM_MODEL`).
3.  Run the script:

    ```bash
    python llm-meshtastic-tools-emb-desc-match.py
    ```

**Dependencies:**

*   `meshtastic`
*   `pubsub`
*   `openai`
*   `httpx`
*   `numpy`
*   `scikit-learn` (for `cosine_similarity`)
*   `llm-mesh-weather.bash` (for weather reports, if used by the `weather_report` tool)

**Configuration:**

The script uses the following variables, which can be modified directly in the script:

*   `LLM_BASE_URL`: The base URL of your local LLM server for chat completions (default: `http://localhost:9090/v1`).
*   `EMBEDDING_BASE_URL`: The base URL of your local LLM server for embeddings (default: `http://localhost:9494/v1`).
*   `LLM_API_KEY`: API key for the LLM (default: `"none"`).
*   `LLM_MODEL`: The name of the LLM model to use for chat (default: `"gemma-3-4b-it-q8_0"`).
*   `LLM_SYSTEM_PROMPT`: System prompt for the LLM (default: `"You are a helpful assistant responding to Meshtastic text messages."`).
*   `LLM_PREPROMPT`: Pre-prompt for the LLM (default: `"The user says: "`).
*   `LLM_POSTPROMPT`: Post-prompt for the LLM (default: `"Respond to the user."`).
*   `LLM_TEMPERATURE`: Temperature for LLM queries (default: `0.7`).
*   `LLM_TIMEOUT`: Timeout for LLM requests in seconds (default: `3600`).
*   `MAX_MESSAGE_LENGTH`: Maximum characters per Meshtastic message chunk (default: `200`).

**Tools:**

The script includes the following tools that can be selected by the LLM based on embedding similarity:

*   `system_info`: Prints system information (CPU usage, memory usage, uptime).
*   `weather_report`: Gives a local weather report (requires `llm-mesh-weather.bash`).
*   `chat`: General chat for jokes, advice, etc.
*   `numbers_station`: Responds with random numbers.

**Note:** This script requires a local LLM server for both chat completions and embeddings to be running and accessible. It automatically attempts to connect to a Meshtastic device. Ensure the `meshtastic` Python library is correctly installed and your device is recognized by the system.
</details>

<details>
<summary>llm-meshtastic-tools.py</summary>

### `llm-meshtastic-tools.py`

**Description:** Listens for Meshtastic text messages, uses an LLM to select and execute a tool based on the message content, and sends the tool's response back to the sender.

**Purpose:** This script acts as an LLM-powered assistant for Meshtastic messages. It can respond to messages by providing system information, weather reports, general chat responses, or random numbers, by dynamically selecting the most relevant tool.

**Usage:**

1.  Ensure your Meshtastic device is connected and accessible (e.g., via USB).
2.  Configure the LLM settings within the script (e.g., `LLM_BASE_URL`, `EMBEDDING_BASE_URL`, `LLM_MODEL`).
3.  Run the script:

    ```bash
    python llm-meshtastic-tools.py
    ```

**Dependencies:**

*   `meshtastic`
*   `pubsub`
*   `openai`
*   `httpx`
*   `numpy`
*   `scikit-learn` (for `cosine_similarity`)
*   `llm-mesh-weather.bash` (for weather reports)

**Configuration:**

The script uses the following variables, which can be modified directly in the script:

*   `LLM_BASE_URL`: The base URL of your local LLM server for chat completions (default: `http://localhost:9090/v1`).
*   `EMBEDDING_BASE_URL`: The base URL of your local LLM server for embeddings (default: `http://localhost:9494/v1`).
*   `LLM_API_KEY`: API key for the LLM (default: `"none"`).
*   `LLM_MODEL`: The name of the LLM model to use for chat (default: `"gemma-3-4b-it-q8_0"`).
*   `LLM_SYSTEM_PROMPT`: System prompt for the LLM (default: `"You are a helpful assistant responding to Meshtastic text messages."`).
*   `LLM_PREPROMPT`: Pre-prompt for the LLM (default: `"The user says: "`).
*   `LLM_POSTPROMPT`: Post-prompt for the LLM (default: `"Respond to the user."`).
*   `LLM_TEMPERATURE`: Temperature for LLM queries (default: `0.7`).
*   `LLM_TIMEOUT`: Timeout for LLM requests in seconds (default: `3600`).
*   `MAX_MESSAGE_LENGTH`: Maximum characters per Meshtastic message chunk (default: `200`).

**Tools:**

The script includes the following tools that can be selected by the LLM:

*   `system_info`: Prints system information (CPU usage, memory usage, uptime).
*   `weather_report`: Gives a local weather report (requires `llm-mesh-weather.bash`).
*   `chat`: General chat for jokes, advice, etc.
*   `numbers_station`: Responds with random numbers.

**Note:** This script requires a local LLM server for both chat completions and embeddings to be running and accessible. It automatically attempts to connect to a Meshtastic device. Ensure the `meshtastic` Python library is correctly installed and your device is recognized by the system.
</details>

<details>
<summary>llm-video-analysis.bash</summary>

### `llm-video-analysis.bash`

**Description:** Analyzes a video from a given URL by extracting frames (either at a fixed rate or based on scene changes), optionally downloading subtitles, and then using an LLM with vision capabilities to describe the video content. It supports both batch processing and interactive prompting.

**Purpose:** This script automates the process of extracting visual and textual information from a video and leveraging an LLM to generate descriptions or answer questions about the video's content. It's useful for summarizing videos, understanding visual events, or extracting key information.

**Usage:**

```bash
./llm-video-analysis.bash [-a|--all-frames] [-s|--scene-change] [-ss|--subtitles] [-c|--cookies] [-nt|--no-title] [-p|--prompt] <video_url>
```

*   `<video_url>`: The URL of the video to analyze.
*   `-a`, `--all-frames`: Optional. Processes all extracted frames at once with the LLM, rather than in batches.
*   `-s`, `--scene-change`: Optional. Extracts frames based on scene changes detected by `ffmpeg` (default threshold: 0.3). If not set, extracts frames at a fixed rate (default: 2 frames/second).
*   `-ss`, `--subtitles`: Optional. Attempts to download and include video subtitles in the LLM's context.
*   `-c`, `--cookies`: Optional. Uses cookies from the Chrome browser for `yt-dlp` to access age-restricted or private videos.
*   `-nt`, `--no-title`: Optional. Skips extracting the video title.
*   `-p`, `--prompt`: Optional. Enables an interactive mode where you can provide multiple prompts to the LLM after initial video processing.

**Dependencies:**

*   `yt-dlp` (external executable)
*   `ffmpeg` (external executable)
*   `bc` (for arithmetic operations)
*   `llm-python-vision-multi-images.py` (for LLM interaction with multiple images)
*   `llm-python-vision-multi-images-file.py` (for LLM interaction with multiple images and a subtitle file)
*   `llm-python-file.py` (for summarizing the output in non-interactive mode)

**Configuration:**

*   Requires `yt-dlp` and `ffmpeg` to be installed and accessible in your system's PATH.
*   Requires `llm-python-vision-multi-images.py`, `llm-python-vision-multi-images-file.py`, and `llm-python-file.py` to be accessible and configured to connect to a local LLM server with vision capabilities.
*   Temporary files (frames, subtitles, analysis output) are stored in `/dev/shm/llm-video-analysis/`.
*   `frame_rate`: Fixed frame extraction rate (default: 2 frames/second).
*   `scene_threshold`: Threshold for scene change detection (default: 0.3).
*   `frames_per_batch`: Number of frames processed per LLM batch in non-`--all-frames` mode (default: 20).
*   LLM server URL and model are configured within the Python scripts it calls.

**Notes:**

*   The script clears the `/dev/shm/llm-video-analysis/` directory on startup.
*   The quality of the video analysis depends on the capabilities of the LLM you are using.
*   Subtitle download attempts both regular and auto-generated subtitles.
</details>

## Video Editing

These scripts provide tools for editing video content using LLMs.

<details>
<summary>llm-ffmpeg-edit.bash</summary>

### `llm-ffmpeg-edit.bash`

**Description:** Detects a specified "thing" in a video using an LLM with vision capabilities and clips the video to include the detected segments. It supports both single continuous segment clipping and full video scanning to concatenate all detected segments.

**Purpose:** This script automates the process of identifying specific visual content within a video and extracting those portions into a new video file. It's useful for creating highlight reels, removing irrelevant sections, or focusing on particular events in a video.

**Usage:**

```bash
./llm-ffmpeg-edit.bash [options] <video_source> <thing_to_detect>
```

*   `<video_source>`: The URL of the video (e.g., `https://www.youtube.com/watch?v=dQw4w9WgXcQ`) or the path to a local video file (when using `--local-file`).
*   `<thing_to_detect>`: A natural language description of what the LLM should look for in the video frames (e.g., `'cat playing piano'`, `'Rick Astley singing'`).

**Options:**

*   `-s`, `--scene-change`: Optional. Extracts frames based on scene changes detected by `ffmpeg` (default threshold: 0.3). If not set, extracts frames at a fixed rate (default: 2 frames/second).
*   `-c`, `--cookies`: Optional. Uses cookies from the Chrome browser for `yt-dlp` to access age-restricted or private videos (only applicable for URL video sources).
*   `-o`, `--output-file <filename>`: Optional. Specifies the name of the output clipped video file (default: `clipped_video.mp4`).
*   `-fr`, `--frame-rate <rate>`: Optional. Sets the frame extraction rate in frames per second (default: 2).
*   `-fb`, `--frames-per-batch <num>`: Optional. Sets the number of frames to send to the LLM per batch for analysis (default: 20).
*   `-f`, `--full`: Optional. If set, the script will scan the full video and concatenate *all* detected segments of the `thing_to_detect`. If not set, it will only clip the *first* continuous segment found.
*   `-l`, `--local-file <path>`: Optional. Specifies that the video source is a local file path instead of a URL.

**Dependencies:**

*   `ffmpeg` (external executable, for video processing and frame extraction)
*   `yt-dlp` (external executable, for downloading videos from URLs)
*   `bc` (for arithmetic operations)
*   `llm-python-vision-multi-images.py` (for LLM interaction with multiple images)

**Configuration:**

*   Requires `ffmpeg` and `yt-dlp` to be installed and accessible in your system's PATH.
*   Requires `llm-python-vision-multi-images.py` to be accessible and configured to connect to a local LLM server with vision capabilities.
*   Temporary files (downloaded video, extracted frames, intermediate clips) are stored in `/dev/shm/llm-ffmpeg-edit/`. This directory is cleared on script startup.
*   The LLM server URL and model are configured within the `llm-python-vision-multi-images.py` script it calls.
*   `scene_threshold`: Threshold for scene change detection (default: 0.3).
*   `temperature`: Temperature for LLM calls (default: 0.15).

**Notes:**

*   The script attempts to use stream copy for clipping for speed, but will fall back to re-encoding if stream copy fails (e.g., due to non-keyframe cut points).
*   The quality of the detection and clipping depends on the capabilities of the LLM you are using and the clarity of the video content.
</details>
