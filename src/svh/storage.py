import json
from pathlib import Path

from svh import notify

# Determine project root relative to this file
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
STORAGE_DIR = PROJECT_ROOT / "storage"
STORAGE_DIR.mkdir(exist_ok=True)


def add(data):
    file_name = data["name"]
    file_path = STORAGE_DIR / file_name
    content = data["content"]

    try:
        parsed_json = json.loads(content)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(parsed_json, f, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    print(f"File saved to: {file_path}")
    return file_path


def read(storage_path):
    file_path = PROJECT_ROOT / storage_path
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        return content
    except FileNotFoundError:
        return None
    except OSError as e:
        raise e
