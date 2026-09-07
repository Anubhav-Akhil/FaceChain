#!/usr/bin/env python3
"""
app.py — Flask web server for the Face ID + Blockchain Verification Pipeline.

Serves a web UI where users can upload images, watch pipeline progress
in real-time via Server-Sent Events (SSE), and browse all matched results.

Usage:
    python app.py
    → Open http://localhost:5000 in your browser
"""

import json
import os
import queue
import sys
import tempfile
import threading
import uuid
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, send_file

# Fix encoding for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload limit

# ── In-memory stores ────────────────────────────────────────────
# run_id → queue.Queue of SSE events
_progress_queues: dict[str, queue.Queue] = {}

# run_id → final results dict
_results_store: dict[str, dict] = {}

# run_id → cropped face path (for serving via /uploads/crop)
_crop_paths: dict[str, str] = {}

# Upload directory
UPLOAD_DIR = Path(tempfile.gettempdir()) / "faceid_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


# ══════════════════════════════════════════════════════════════════
#  Routes
# ══════════════════════════════════════════════════════════════════


@app.route("/")
def index():
    """Serve the main web UI."""
    return render_template("index.html")


@app.route("/api/run", methods=["POST"])
def api_run():
    """
    Accept an image upload and start the pipeline in a background thread.
    Returns a run_id that the client uses to connect to the SSE stream.
    """
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Save uploaded file
    run_id = str(uuid.uuid4())[:8]
    ext = Path(file.filename).suffix or ".jpg"
    upload_path = str(UPLOAD_DIR / f"{run_id}{ext}")
    file.save(upload_path)

    model = request.form.get("model", "dnn")

    # Create progress queue
    q = queue.Queue()
    _progress_queues[run_id] = q

    # Run pipeline in background thread
    thread = threading.Thread(
        target=_run_pipeline_thread,
        args=(run_id, upload_path, model, q),
        daemon=True,
    )
    thread.start()

    return jsonify({"run_id": run_id})


@app.route("/api/progress/<run_id>")
def api_progress(run_id):
    """SSE endpoint — streams pipeline progress events to the client."""
    if run_id not in _progress_queues:
        return jsonify({"error": "Unknown run_id"}), 404

    def generate():
        q = _progress_queues[run_id]
        while True:
            try:
                event = q.get(timeout=120)  # 2 minute timeout
            except queue.Empty:
                # Send keepalive comment
                yield ": keepalive\n\n"
                continue

            if event is None:
                # Sentinel: pipeline finished
                break

            event_type = event.get("type", "progress")
            data = json.dumps(event.get("data", {}), default=str)
            yield f"event: {event_type}\ndata: {data}\n\n"

        # Cleanup
        _progress_queues.pop(run_id, None)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/api/results/<run_id>")
def api_results(run_id):
    """Return stored results for a completed run."""
    if run_id not in _results_store:
        return jsonify({"error": "Results not found"}), 404
    return jsonify(_results_store[run_id])


@app.route("/uploads/crop")
def serve_crop():
    """Serve the most recent cropped face image."""
    # Find the most recent crop
    crop_path = None
    for rid in reversed(list(_crop_paths.keys())):
        p = _crop_paths[rid]
        if os.path.isfile(p):
            crop_path = p
            break

    if not crop_path:
        # Fallback: try temp directory
        fallback = os.path.join(tempfile.gettempdir(), "temp_face_crop.jpg")
        if os.path.isfile(fallback):
            crop_path = fallback

    if crop_path and os.path.isfile(crop_path):
        return send_file(crop_path, mimetype="image/jpeg")
    return "", 404


# ══════════════════════════════════════════════════════════════════
#  Pipeline Runner (background thread)
# ══════════════════════════════════════════════════════════════════


def _run_pipeline_thread(
    run_id: str, image_path: str, model: str, q: queue.Queue
):
    """Run the pipeline and push progress events to the queue."""
    from src.pipeline import run_with_progress

    def on_progress(stage: str, status: str, data: dict):
        """Callback invoked by the pipeline for each stage transition."""
        q.put({
            "type": "progress",
            "data": {
                "stage": stage,
                "status": status,
                "data": data,
            },
        })

    try:
        results = run_with_progress(
            image_path=image_path,
            model=model,
            verbose=False,
            on_progress=on_progress,
        )

        # Store results
        _results_store[run_id] = results

        # Store crop path
        fd = results.get("stages", {}).get("face_detection", {})
        if fd.get("cropped_path"):
            _crop_paths[run_id] = fd["cropped_path"]

        # Send final result event
        q.put({
            "type": "result",
            "data": results,
        })

    except Exception as e:
        q.put({
            "type": "error_event",
            "data": {
                "error": str(e),
                "partial_results": _results_store.get(run_id),
            },
        })

    finally:
        # Sentinel to close SSE stream
        q.put(None)


# ══════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n  🧠 Face ID + Blockchain Pipeline — Web UI")
    print("  ─────────────────────────────────────────")
    print("  Open http://localhost:5000 in your browser\n")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        threaded=True,
    )
