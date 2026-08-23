import pathlib
import py_compile

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILES = [
    "config.py", "database.py", "memory.py", "family_profiles.py", "ai.py", "router.py", "main.py", "tool_schema.py",
    "backend/api.py", "backend/live_voice.py", "integrations_lg.py", "integrations_smartthings.py", "home_tools.py", "tests/test_home_contracts.py", "backend/voice_service.py", "backend/activation.py",
    "tools/calculator.py", "tools/music.py", "tools/news.py", "tools/system.py", "tools/weather.py", "tools/web.py",
    "companion_clap.py", "devices/base.py", "devices/ir_blaster.py", "run.py",
]
for rel in FILES:
    py_compile.compile(str(ROOT / rel), doraise=True)
    print("OK", rel)
print("STATIC BACKEND COMPILE OK")
