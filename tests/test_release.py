from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_structure():
    required = [
        "run.py", "backend/api.py", "home_tools.py", "devices/base.py", "devices/ir_blaster.py",
        "integrations_lg.py", "integrations_smartthings.py", "frontend/package.json",
        "data/ir_devices.example.json", ".env.example", "README.md",
    ]
    for rel in required:
        assert (ROOT / rel).exists(), rel


def test_no_secret_values_in_env_example():
    text = (ROOT / ".env.example").read_text()
    forbidden_markers = ["AQ.Ab8", "thinqpat_", "b532251b", "ecc4343f"]
    assert not any(marker in text for marker in forbidden_markers)
