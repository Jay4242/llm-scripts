# llm-scripts
Random llm scripts


### llm-conv.py

llm Python conversation script.

Takes a system prompt, user prompt, and temperature as a parameter then starts a chat.

It doesn't check context length at all so eventually a chat on all of these that use the same method would hit the limit and be handled however the software handles context limits.


### llm-file-conv.py

llm Python file conversation script.

Basically the same as `llm-conv.py` except it loads a file chosen as a parameter to be loaded into the context.


### llm-file-conv-pygame.py

The same as `llm-file-conv.py` except it tries to display things in a pygame screen simultaneously.

The pygame screen does not currently display the text correctly.


### llm-conv-file-memory.py

My attempt at a memory implementation where you load a memory text file and ask the bot if it wants to update the text file.
