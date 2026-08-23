from __future__ import annotations

import json

from home_tools import home_list_devices

if __name__ == "__main__":
    result = home_list_devices()
    print(json.dumps(result, indent=2, ensure_ascii=False))
