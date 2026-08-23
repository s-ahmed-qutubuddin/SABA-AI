from pathlib import Path
import shutil
ROOT = Path(__file__).resolve().parents[1]
example = ROOT / "family_profiles.example.json"
out = ROOT / "family_profiles.json"
if not out.exists():
    shutil.copy2(example, out)
print(out)
