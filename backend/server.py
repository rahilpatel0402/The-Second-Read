"""The Second Read - FastAPI backend (serves API + the static frontend)."""
import json
import os
import queue
import threading

from fastapi import FastAPI
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from pydantic import BaseModel

from chart import list_charts, load_chart, default_chart, normalize_import
from agent import run_review

app = FastAPI(title="The Second Read")

FRONTEND = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")


class ReviewRequest(BaseModel):
    chart_id: str | None = None
    chart: dict | None = None       # a full chart (e.g. an imported one)
    note: str | None = None         # overrides note_under_review text


class ImportRequest(BaseModel):
    data: dict | list


@app.get("/api/charts")
def api_charts():
    return JSONResponse({"charts": list_charts()})


@app.get("/api/chart/{chart_id}")
def api_chart(chart_id: str):
    c = load_chart(chart_id)
    if not c:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(c)


@app.post("/api/import")
def api_import(req: ImportRequest):
    try:
        return JSONResponse(normalize_import(req.data))
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/api/review")
def api_review(req: ReviewRequest):
    chart = req.chart or (load_chart(req.chart_id) if req.chart_id else None) or default_chart()
    if not chart:
        return JSONResponse({"error": "no chart available"}, status_code=400)
    note_text = req.note if (req.note and req.note.strip()) else chart["note_under_review"]["text"]

    q: "queue.Queue" = queue.Queue()
    SENTINEL = object()

    def emit(event):
        q.put(event)

    def worker():
        try:
            run_review(chart, note_text, emit)
        except Exception as e:  # surface errors to the UI instead of hanging
            q.put({"type": "error", "message": f"{type(e).__name__}: {e}"})
        finally:
            q.put(SENTINEL)

    threading.Thread(target=worker, daemon=True).start()

    def stream():
        while True:
            event = q.get()
            if event is SENTINEL:
                break
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@app.get("/")
def index():
    return FileResponse(FRONTEND)
