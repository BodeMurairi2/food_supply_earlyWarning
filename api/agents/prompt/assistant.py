"""The user message for one AI assistant request."""

import json
from datetime import date

from google.genai import types

PAGES = {
    "prediction": "Prediction Lab: the user ran the model on this district and year, possibly with their own inputs.",
    "forecast": "Forecasts: the model's forecast for this district and year.",
    "visualization": "Visualizations: the trend the user is looking at for this area. Explain the trend, then what it implies for food security.",
}


def build_message(kind, context):
    payload = {"page": PAGES[kind], "today": date.today().isoformat(), **context}
    prompt = "RESULT CONTEXT:\n" + json.dumps(payload, ensure_ascii=False)
    return types.Content(role="user", parts=[types.Part(text=prompt)])
