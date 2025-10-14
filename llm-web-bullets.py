#!/usr/bin/env python3
"""
llm-web-bullets.py

Fetch one or more webpages, extract the visible text from the <body> using BeautifulSoup,
and send each to a local LLM backend (compatible with OpenAI's client API) for summarization.
The script accepts multiple URLs as positional arguments and an optional ``--debug`` flag.
Prompts, model, and temperature are hard‑coded within the script.

Usage:
    python llm-web-bullets.py <url1> [<url2> ...] [--debug]

Example:
    python llm-web-bullets.py https://example.com https://example.org --debug
"""

import argparse
import sys
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import httpx
from typing import Dict, List, Optional
import datetime

CURRENT_DATE = datetime.date.today().isoformat()

# Base URL for the local LLM backend – change in one place if needed.
BASE_URL = "http://localhost:9090/v1"

# Configuration variables – adjust here to change the LLM client behavior.
API_KEY = "None"
TIMEOUT = httpx.Timeout(3600)
USER_AGENT = "llm-web-bullets/1.0"
MODEL = "Qwen3-30B-A3B-Instruct-2507-Q8_0"
TEMPERATURE = 0.0  # default temperature, adjust as needed
SEARX_BASE_URL = "http://searx.lan"

def fetch_body_text(url: str) -> str:
    """Download the page at *url* and return the cleaned body text."""
    response = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    # Prefer the <body> tag; fall back to the whole document if missing.
    if soup.body:
        return soup.body.get_text(separator="\n", strip=True)
    return soup.get_text(separator="\n", strip=True)


def generate_search_terms(question: str) -> str:
    """
    Ask the LLM to produce a concise search query for SearxNG based on the user's question.
    """
    system_prompt = f"You are an assistant that converts user questions into short search queries. Today is {CURRENT_DATE}."
    user_prompt = f"Question: {question}\nGenerate a short search query suitable for a news search."
    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
        timeout=TIMEOUT,
    )
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        stream=False,
    )
    return completion.choices[0].message.content.strip()


def searxng_news_search(query: str, time_range: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Query the SearxNG instance at http://searx.lan for news results.
    Returns a list of dictionaries with keys: title, url, content.
    """
    search_url = f"{SEARX_BASE_URL}/search"
    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    time_range_param = f"&time_range={time_range}" if time_range else ""
    data = f"q={query}&categories=news&language=auto{time_range_param}&safesearch=0&theme=simple"
    response = requests.post(search_url, headers=headers, data=data, verify=False, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    results: List[Dict[str, str]] = []
    for article in soup.find_all("article", class_="result")[:30]:
        url_header = article.find("a", class_="url_header")
        if not url_header:
            continue
        url = url_header["href"]
        title = article.find("h3").get_text(strip=True) if article.find("h3") else "No Title"
        description = (
            article.find("p", class_="content").get_text(strip=True)
            if article.find("p", class_="content")
            else ""
        )
        results.append({"title": title, "url": url, "content": description})
    return results


def select_time_range(question: str) -> str:
    """
    Ask the LLM to choose a time range (day, week, month, year) for a news search
    based on the provided question. Returns the chosen time range as a string.
    """
    system_prompt = f"You are an assistant that selects an appropriate time range for news searches. Today is {CURRENT_DATE}."
    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
        timeout=TIMEOUT,
    )
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Question: {question}"},
            {
                "role": "user",
                "content": (
                    "Based on the question, choose a time range for searching news. "
                    "Options are: day, week, month, year. Respond with only the chosen option."
                ),
            },
        ],
        temperature=0.0,
        stream=False,
    )
    answer = completion.choices[0].message.content.strip().lower()
    # Validate answer; default to None if not recognized
    if answer in {"day", "week", "month", "year"}:
        return answer
    return None


def is_relevant(question: str, title: str, description: str) -> bool:
    """
    Ask the LLM whether a news article (title + description) is relevant to the question.
    Returns True if the LLM answers affirmatively.
    """
    system_prompt = f"You are a relevance classifier. Today is {CURRENT_DATE}."
    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
        timeout=TIMEOUT,
    )
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Question: {question}"},
            {"role": "user", "content": f"Article Title: {title}"},
            {"role": "user", "content": f"Article Description: {description}"},
            {"role": "user", "content": "Answer with ONLY 'YES' if the article is relevant, otherwise answer with ONLY 'NO'."},
        ],
        temperature=0.0,
        stream=False,
    )
    answer = completion.choices[0].message.content.strip().upper()
    return answer == "YES"


def summarize(document: str, url: str) -> str:
    """Send *document* to the local LLM backend and return the streamed summary."""
    system_prompt = f"You are a helpful assistant. Today is {CURRENT_DATE}."
    pre_prompt = f"The following is the text from {url}:"
    post_prompt = "Create a complete but concise multi-tier bullet point summary of this article."
    temperature = TEMPERATURE  # configurable temperature

    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
        timeout=TIMEOUT,
    )

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": pre_prompt},
            {"role": "user", "content": document},
            {"role": "user", "content": post_prompt},
        ],
        temperature=temperature,
        stream=True,
    )

    result = ""
    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content:
            result += chunk.choices[0].delta.content
    return result


def reconcile(summaries: Dict[str, str]) -> str:
    """
    Send the collected bullet‑point summaries to the LLM backend and ask it to
    reconcile them into a cohesive summary.

    *summaries* is a mapping of URL → bullet‑point summary.
    """
    system_prompt = f"You are a helpful assistant. Today is {CURRENT_DATE}."
    # Build the message list with a separate user entry for each URL and its summary.
    messages = [{"role": "system", "content": system_prompt}]

    for url, summary in summaries.items():
        messages.append(
            {"role": "user", "content": f"The following is the bullet point summary of {url}:"}
        )
        messages.append({"role": "user", "content": summary})

    # Final instruction to the model.
    messages.append(
        {
            "role": "user",
            "content": "Please reconcile these summaries into a single concise multi‑tier bullet point summary.",
        }
    )

    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
        timeout=TIMEOUT,
    )

    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
        stream=True,
    )

    result = ""
    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta.content:
            result += chunk.choices[0].delta.content
    return result

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch webpages, summarize them with an LLM, and reconcile the summaries."
    )
    parser.add_argument(
        "urls",
        nargs="*",
        help="One or more URLs to process (ignored if --websearch is used).",
    )
    parser.add_argument(
        "--websearch",
        type=str,
        help="Perform a websearch for the given question instead of using explicit URLs.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debug information to stderr.",
    )
    args = parser.parse_args()

    debug = args.debug
    if args.websearch:
        question = args.websearch
        # Generate a search query from the question using the LLM.
        search_query = generate_search_terms(question)
        if debug:
            print(f"[DEBUG] Generated search query: {search_query}", file=sys.stderr)

        # Determine appropriate time range for the news search.
        time_range = select_time_range(question)
        if debug:
            print(f"[DEBUG] Selected time range: {time_range}", file=sys.stderr)

        # Retrieve news results from the SearxNG instance.
        news_results = searxng_news_search(search_query, time_range)
        if debug:
            print(f"[DEBUG] Retrieved {len(news_results)} news results", file=sys.stderr)

        # Filter results based on relevance to the original question.
        urls = []
        for result in news_results:
            title = result.get("title", "")
            description = result.get("content", "")
            url = result.get("url", "")
            relevance = is_relevant(question, title, description)
            if debug:
                print("[DEBUG] Evaluating article:", file=sys.stderr)
                print(f"  URL: {url}", file=sys.stderr)
                print(f"  Title: {title}", file=sys.stderr)
                print(f"  Description: {description}", file=sys.stderr)
                print(f"  Relevant: {relevance}", file=sys.stderr)
            if relevance:
                urls.append(url)
    else:
        urls = args.urls

    # Collect summaries for each URL.
    summaries: Dict[str, str] = {}
    for url in urls:
        document = fetch_body_text(url)
        if debug:
            print(f"[DEBUG] Cleaned body text for {url}:", file=sys.stderr)
            print(document, file=sys.stderr)
            print("-" * 80, file=sys.stderr)

        summary = summarize(document, url)
        if debug:
            print(f"[DEBUG] Bullet‑point summary for {url}:", file=sys.stderr)
            print(summary, file=sys.stderr)
            print("-" * 80, file=sys.stderr)

        summaries[url] = summary

    # Reconcile all summaries into a single output.
    final_summary = reconcile(summaries)

    print(final_summary)


if __name__ == "__main__":
    main()
