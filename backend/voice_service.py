"""Legacy compatibility module.

The active voice implementation is backend.live_voice, which uses the Gemini Live API
for bidirectional audio. This file remains so older imports do not fail.
"""

class VoiceService:
    def start(self):
        return {"already_running": False, "message": "Use the frontend Gemini Live session."}

    def stop(self):
        return {"state": "stopped"}

    @property
    def state(self):
        class State:
            value = "stopped"
        return State()

    @property
    def conversation_id(self):
        return None
