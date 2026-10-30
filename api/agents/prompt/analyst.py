"""The user message for one analysis: the model context, and the question if there is one."""

import json

from google.genai import types


def build_message(context, question=None):
    prompt = "MODEL CONTEXT:\n" + json.dumps(context, ensure_ascii=False)
    if question:
        prompt += f"\n\nUSER QUESTION (research this too): {question}"
    return types.Content(role="user", parts=[types.Part(text=prompt)])
