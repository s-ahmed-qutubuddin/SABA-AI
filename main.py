"""Jamal Family Assistant entry point.

The production app is run through FastAPI so the React frontend and Gemini Live voice
session can share the same backend. Use START_JAMAL_ASSISTANT.command or:

    python -m uvicorn backend.api:app --reload --port 8000
"""

if __name__ == "__main__":
    print("JAMAL FAMILY ASSISTANT")
    print("Assistant: Saba")
    print("No wake word. Start voice from the frontend.")
    print("Run: python -m uvicorn backend.api:app --reload --port 8000")
