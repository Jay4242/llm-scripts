#!/usr/bin/env python3
"""
A simple teleprompter that displays lines of text, records the user's voice,
and uses an LLM backend to verify that the spoken audio roughly matches the
displayed text.

Usage:
    python llm-teleprompter.py <script.txt>

The script file should contain one line of text per prompt.  For each line the
program will:

1. Show the line in a pygame window.
2. Wait for the user to press the SPACE bar to start recording.
3. Record a fixed duration of audio (default 5 seconds) from the microphone.
4. Send the text and the recorded audio to the LLM backend (via OpenAI‑compatible
   API) and ask it to answer “True” if the audio matches the text, otherwise
   “False”.
5. If the answer is True the audio file is saved as ``audio_XXXXX.wav`` and the
   program proceeds to the next line; otherwise the user can try again.

Dependencies:
    pip install pygame sounddevice numpy openai
"""

import sys
import os
import time
import base64
import wave
import pygame
import sounddevice as sd
import numpy as np
from openai import OpenAI

import warnings
warnings.filterwarnings(
    "ignore",
    message="Process running 'fc-list' timed-out!*",
    module="pygame.sysfont",
)

# Custom pygame timer event for periodic redraws
REDRAW_EVENT = pygame.USEREVENT + 1
REDRAW_INTERVAL_MS = 500  # Redraw every 500 ms

# ---------------------------------------------------------------------------

# Configuration
RECORD_SECONDS = 5          # Fixed recording length
SAMPLE_RATE = 44100         # Sample rate for recording (44.1 kHz)
AUDIO_DTYPE = 'int16'        # 16‑bit PCM
SAMPLE_WIDTH = 2             # 2 bytes = 16‑bit audio
AUDIO_DIR = "recordings"    # Base directory for recordings
MODEL = "Qwen2.5-Omni-3B-Q8_0"
API_BASE = "http://localhost:9090/v1"
API_KEY = "none"

# Ensure the recordings directory exists
os.makedirs(AUDIO_DIR, exist_ok=True)

def record_audio(filename: str) -> None:
    """Record audio from the default microphone until SPACE is pressed again, then save as a WAV file."""
    print("Recording... Press SPACE again to stop.")
    frames = []

    def _callback(indata, frames_count, time_info, status):
        # Copy the incoming audio data to our list
        frames.append(indata.copy())

    # Start an input stream that calls our callback with each chunk of audio
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype=AUDIO_DTYPE, callback=_callback):
        recording = True
        while recording:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    recording = False
                    break
            sd.sleep(100)  # Small sleep to avoid busy‑waiting
            # Ensure pygame continues processing events to keep the window responsive
            pygame.event.pump()

    # Concatenate all captured chunks into a single NumPy array
    audio = np.concatenate(frames, axis=0)
    # No conversion needed for int16 audio

    # Write the captured audio to a WAV file
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(SAMPLE_WIDTH)  # 24‑bit audio
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())
    print(f"Saved recording to {filename}")

def audio_to_base64(path: str) -> str:
    """Read a WAV file and return its base64‑encoded contents."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """
    Split *text* into a list of lines that fit within *max_width* pixels
    when rendered with *font*. Simple greedy word‑wrap algorithm.
    """
    words = text.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

def evaluate_match(text: str, audio_path: str) -> bool:
    """
    Send the target text and the recorded audio to the LLM backend.
    The system prompt asks the model to answer with a plain ``True`` or ``False``.
    """
    client = OpenAI(base_url=API_BASE, api_key=API_KEY)

    base64_audio = audio_to_base64(audio_path)

    # Build the request messages
    messages = [
        {"role": "system", "content": (
            "You are a strict evaluator. Given a piece of text and an audio recording, respond with only the word True if the spoken audio roughly matches the text, otherwise respond with only the word False."
        )},
        {"role": "user", "content": [
            {"type": "text", "text": text},
            {
                "type": "input_audio",
                "input_audio": {"data": base64_audio, "format": "wav"},
            },
        ]},
    ]

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=5,
            temperature=0.0,
        )
        response = completion.choices[0].message.content.strip()
        return response.lower() == "true"
    except Exception as exc:
        print(f"Error during LLM evaluation: {exc}")
        return False

def display_line(screen, font, line: str) -> None:
    """
    Render *line* on the pygame screen, wrapping it if it exceeds the window width.
    The wrapped lines are vertically centered.
    """
    screen.fill((0, 0, 0))

    padding = 20  # pixels on left/right
    max_width = screen.get_width() - 2 * padding
    wrapped_lines = _wrap_text(line, font, max_width)

    line_height = font.get_height()
    spacing = 5  # pixels between lines
    total_height = len(wrapped_lines) * line_height + (len(wrapped_lines) - 1) * spacing
    start_y = (screen.get_height() - total_height) // 2

    for i, txt in enumerate(wrapped_lines):
        text_surface = font.render(txt, True, (255, 255, 255))
        text_rect = text_surface.get_rect()
        text_rect.centerx = screen.get_rect().centerx
        text_rect.y = start_y + i * (line_height + spacing)
        screen.blit(text_surface, text_rect)

    pygame.display.flip()

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python llm-teleprompter.py <script.txt>")
        sys.exit(1)

    script_path = sys.argv[1]
    if not os.path.isfile(script_path):
        print(f"Script file not found: {script_path}")
        sys.exit(1)

    # Create a subdirectory for recordings named after the script file
    recordings_subdir = os.path.join(AUDIO_DIR, os.path.basename(script_path))
    os.makedirs(recordings_subdir, exist_ok=True)

    # Load lines from the script file
    with open(script_path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    # Initialize pygame
    pygame.init()
    screen = pygame.display.set_mode((800, 200))
    pygame.display.set_caption("LLM Teleprompter")
    font = pygame.font.SysFont(None, 48)

    line_index = 0
    attempt = 0

    while line_index < len(lines):
        line = lines[line_index]
        display_line(screen, font, line)
        # Start periodic redraw to keep the window responsive when not in foreground
        pygame.time.set_timer(REDRAW_EVENT, REDRAW_INTERVAL_MS)

        print(f"\nLine {line_index + 1}/{len(lines)}: \"{line}\"")
        print("Press SPACE to start recording, or ESC to quit.")

        # Wait for user input (SPACE to start recording, ESC to quit) while keeping CPU usage low.
        waiting = True
        skip_record = False
        while waiting:
            # Block until the next event arrives to avoid a busy‑loop.
            event = pygame.event.wait()
            # Process the received event.
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit(0)
                elif event.key == pygame.K_SPACE:
                    waiting = False
                elif event.key == pygame.K_LEFT:
                    # Move back to previous line
                    line_index = max(0, line_index - 1)
                    attempt = 0
                    skip_record = True
                    waiting = False
                elif event.key == pygame.K_RIGHT:
                    # Move forward to next line
                    line_index = min(len(lines) - 1, line_index + 1)
                    attempt = 0
                    skip_record = True
                    waiting = False
            elif event.type == REDRAW_EVENT:
                display_line(screen, font, line)

            # Drain any additional queued events to keep the UI responsive.
            for extra_event in pygame.event.get():
                if extra_event.type == REDRAW_EVENT:
                    display_line(screen, font, line)

        # Record audio (skip if navigation key pressed)
        if skip_record:
            continue
        timestamp = int(time.time())
        audio_filename = os.path.join(
            recordings_subdir,
            f"audio_{line_index + 1:05d}_{attempt:02d}_{timestamp}.wav"
        )
        record_audio(audio_filename)

        # Keep pygame responsive before evaluation
        pygame.event.pump()
        # Show a temporary “Evaluating...” message so the user sees progress
        display_line(screen, font, "Evaluating...")
        pygame.event.pump()

        # Evaluate with LLM
        print("Evaluating audio against the target text...")
        if evaluate_match(line, audio_filename):
            print("✅ Match confirmed! Moving to next line.")
            # Stop the periodic redraw timer before advancing
            pygame.time.set_timer(REDRAW_EVENT, 0)
            line_index += 1
            attempt = 0
        else:
            print("❌ Mismatch. Please try again.")
            attempt += 1
            # Optionally keep the failed recording for debugging; otherwise delete it
            os.remove(audio_filename)

    print("\nAll lines completed! Well done.")
    pygame.quit()

if __name__ == "__main__":
    main()
