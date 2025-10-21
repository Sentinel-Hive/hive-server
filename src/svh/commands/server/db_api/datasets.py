from fastapi import UploadFile
from svh.commands.db.config.settings import get_settings
import os

settings = get_settings()

def save_dataset_file(file: UploadFile, filename: str) -> dict:
    try:
        path = os.path.join(settings.datasets_folder, filename)
        with open(path, "wb") as f:
            f.write(file.file.read())
        return {"status": "success", "detail": f"Saved to {path}"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
