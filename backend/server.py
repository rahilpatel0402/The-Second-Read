"""The Second Read - FastAPI backend (serves API + the static frontend)."""
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from chart import list_charts, load_chart, default_chart, normalize_import
from agent import analyze

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
    try:
        return JSONResponse(analyze(chart, note_text))
    except Exception as e:  # surface errors to the UI instead of a blank modal
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)


@app.get("/")
def index():
    return FileResponse(FRONTEND)
