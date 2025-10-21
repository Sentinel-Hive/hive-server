from fastapi import APIRouter, Request, UploadFile, File
from typing import List, Optional
from svh import notify
from svh.commands.server.db_api.datasets import save_dataset_file

router = APIRouter()

@router.post("/ingest")
async def ingest(request: Request, files: Optional[List[UploadFile]] = File(None)):
    try:
        if files:
            results = []
            for file in files:
                result = save_dataset_file(file, file.filename)
                results.append(result)
            notify.server(f"Received {len(files)} file(s) via multipart/form-data")
            return {"status": "received", "files": results}

        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = await request.json()
            # Handle JSON-based ingestion if needed
            notify.server(f"Received JSON payload for ingestion")
            return {"status": "received", "detail": "JSON ingestion not implemented"}

        notify.error(f"Unsupported Content-Type: {content_type}")
        return {
            "status": "error",
            "detail": f"Unsupported Content-Type: {content_type}",
        }

    except Exception as e:
        notify.error(f"Error processing ingestion request: {e}")
        return {"status": "error", "detail": str(e)}
