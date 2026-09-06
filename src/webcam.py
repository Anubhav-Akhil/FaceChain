"""
webcam.py — Live Webcam Mode: real-time face detection + on-demand pipeline trigger.

Opens the system webcam, continuously detects faces using OpenCV YuNet ONNX,
draws bounding boxes, and lets the user press SPACE to capture a frame and
run the full Face ID + Blockchain pipeline on it.

Controls:
    SPACE  — capture current frame and run pipeline
    Q/ESC  — quit
"""

import os
import tempfile
import time

import cv2
import numpy as np

from .face_detector import _load_yunet_detector
from .utils import console


# ── Drawing constants ────────────────────────────────────────────
_BOX_COLOR = (0, 255, 180)       # Bright cyan-green for face box
_BOX_THICKNESS = 2
_TEXT_COLOR = (255, 255, 255)    # White for text
_HUD_BG = (30, 30, 30)          # Dark background for HUD bar
_CAPTURE_COLOR = (0, 120, 255)  # Orange flash on capture
_FONT = cv2.FONT_HERSHEY_SIMPLEX
_FONT_SCALE = 0.55
_FONT_THICKNESS = 1


def _draw_face_boxes(frame: np.ndarray, faces, confidence_threshold: float = 0.5):
    """Draw bounding boxes and confidence scores on detected faces."""
    if faces is None:
        return 0

    count = 0
    for f in faces:
        fx, fy, fw, fh = int(f[0]), int(f[1]), int(f[2]), int(f[3])
        conf = float(f[-1])

        if conf < confidence_threshold:
            continue

        count += 1

        # Draw rectangle
        cv2.rectangle(frame, (fx, fy), (fx + fw, fy + fh), _BOX_COLOR, _BOX_THICKNESS)

        # Draw corner accents (modern look)
        corner_len = min(fw, fh) // 4
        # Top-left
        cv2.line(frame, (fx, fy), (fx + corner_len, fy), _BOX_COLOR, _BOX_THICKNESS + 1)
        cv2.line(frame, (fx, fy), (fx, fy + corner_len), _BOX_COLOR, _BOX_THICKNESS + 1)
        # Top-right
        cv2.line(frame, (fx + fw, fy), (fx + fw - corner_len, fy), _BOX_COLOR, _BOX_THICKNESS + 1)
        cv2.line(frame, (fx + fw, fy), (fx + fw, fy + corner_len), _BOX_COLOR, _BOX_THICKNESS + 1)
        # Bottom-left
        cv2.line(frame, (fx, fy + fh), (fx + corner_len, fy + fh), _BOX_COLOR, _BOX_THICKNESS + 1)
        cv2.line(frame, (fx, fy + fh), (fx, fy + fh - corner_len), _BOX_COLOR, _BOX_THICKNESS + 1)
        # Bottom-right
        cv2.line(frame, (fx + fw, fy + fh), (fx + fw - corner_len, fy + fh), _BOX_COLOR, _BOX_THICKNESS + 1)
        cv2.line(frame, (fx + fw, fy + fh), (fx + fw, fy + fh - corner_len), _BOX_COLOR, _BOX_THICKNESS + 1)

        # Confidence label
        label = f"{conf:.0%}"
        (tw, th), _ = cv2.getTextSize(label, _FONT, _FONT_SCALE, _FONT_THICKNESS)
        cv2.rectangle(frame, (fx, fy - th - 8), (fx + tw + 6, fy), _BOX_COLOR, -1)
        cv2.putText(frame, label, (fx + 3, fy - 4), _FONT, _FONT_SCALE,
                    (0, 0, 0), _FONT_THICKNESS, cv2.LINE_AA)

    return count


def _draw_hud(frame: np.ndarray, num_faces: int, fps: float, processing: bool = False):
    """Draw the heads-up display bar at the top of the frame."""
    h, w = frame.shape[:2]
    bar_height = 40

    # Semi-transparent dark bar at top
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, bar_height), _HUD_BG, -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Left: face count
    face_text = f"Faces: {num_faces}"
    face_color = (0, 255, 120) if num_faces > 0 else (100, 100, 100)
    cv2.putText(frame, face_text, (12, 27), _FONT, _FONT_SCALE,
                face_color, _FONT_THICKNESS, cv2.LINE_AA)

    # Center: FPS
    fps_text = f"FPS: {fps:.0f}"
    (tw, _), _ = cv2.getTextSize(fps_text, _FONT, _FONT_SCALE, _FONT_THICKNESS)
    cv2.putText(frame, fps_text, (w // 2 - tw // 2, 27), _FONT, _FONT_SCALE,
                (200, 200, 200), _FONT_THICKNESS, cv2.LINE_AA)

    # Right: controls
    ctrl_text = "SPACE: Capture  |  Q: Quit"
    (tw, _), _ = cv2.getTextSize(ctrl_text, _FONT, _FONT_SCALE - 0.05, _FONT_THICKNESS)
    cv2.putText(frame, ctrl_text, (w - tw - 12, 27), _FONT, _FONT_SCALE - 0.05,
                (180, 180, 180), _FONT_THICKNESS, cv2.LINE_AA)

    # Processing overlay
    if processing:
        # Full-screen semi-transparent overlay
        proc_overlay = frame.copy()
        cv2.rectangle(proc_overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(proc_overlay, 0.5, frame, 0.5, 0, frame)

        msg = "PROCESSING... Running pipeline"
        (tw, th), _ = cv2.getTextSize(msg, _FONT, 0.9, 2)
        cv2.putText(frame, msg, (w // 2 - tw // 2, h // 2),
                    _FONT, 0.9, _CAPTURE_COLOR, 2, cv2.LINE_AA)

    # Bottom status bar when no face
    if num_faces == 0 and not processing:
        msg = "No face detected — position your face in front of the camera"
        (tw, th), _ = cv2.getTextSize(msg, _FONT, _FONT_SCALE, _FONT_THICKNESS)
        y_pos = h - 20
        cv2.rectangle(frame, (0, y_pos - th - 12), (w, h), _HUD_BG, -1)
        cv2.putText(frame, msg, (w // 2 - tw // 2, y_pos - 4), _FONT, _FONT_SCALE,
                    (0, 140, 255), _FONT_THICKNESS, cv2.LINE_AA)


def run_webcam(
    model: str = "dnn",
    verbose: bool = False,
    camera_index: int = 0,
    confidence_threshold: float = 0.5,
):
    """
    Run the live webcam mode with real-time face detection.

    Parameters
    ----------
    model : str
        Face detection model — "dnn" (default, recommended) or "haar".
    verbose : bool
        Enable verbose pipeline output.
    camera_index : int
        OpenCV camera index (0 = default webcam).
    confidence_threshold : float
        Minimum confidence for face detections (0.0–1.0).
    """
    console.print(
        "\n[bold bright_cyan]📹 Live Webcam Mode[/]"
        "\n   Starting camera…"
    )

    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        console.print("[bold red]ERROR:[/] Could not open webcam. "
                       "Check that a camera is connected and not in use by another app.")
        return

    # Get camera resolution
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    console.print(f"   Camera: {frame_w}×{frame_h}")
    console.print(f"   Model : OpenCV {model.upper()}")
    console.print("   [dim]Press SPACE to capture & run pipeline, Q to quit[/]\n")

    # Load face detector once
    detector = None
    haar_cascade = None

    if model == "dnn":
        detector = _load_yunet_detector(frame_w, frame_h, confidence_threshold)
    else:
        haar_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

    window_name = "Face ID Pipeline — Live Webcam"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

    # FPS tracking
    prev_time = time.time()
    fps = 0.0
    capture_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                console.print("[bold red]ERROR:[/] Failed to read from webcam.")
                break

            # Mirror the frame for natural interaction
            frame = cv2.flip(frame, 1)

            # ── Detect faces ─────────────────────────────────────
            num_faces = 0

            if model == "dnn" and detector is not None:
                # Update input size if frame size changed
                h, w = frame.shape[:2]
                if w != frame_w or h != frame_h:
                    frame_w, frame_h = w, h
                    detector.setInputSize((w, h))

                _, raw_faces = detector.detect(frame)
                num_faces = _draw_face_boxes(frame, raw_faces, confidence_threshold)

            elif haar_cascade is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                detections = haar_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
                )
                for (x, y, fw, fh) in detections:
                    cv2.rectangle(frame, (x, y), (x + fw, y + fh), _BOX_COLOR, _BOX_THICKNESS)
                    num_faces += 1

            # ── FPS calculation ──────────────────────────────────
            curr_time = time.time()
            dt = curr_time - prev_time
            if dt > 0:
                fps = 0.8 * fps + 0.2 * (1.0 / dt)  # Smoothed FPS
            prev_time = curr_time

            # ── Draw HUD ─────────────────────────────────────────
            _draw_hud(frame, num_faces, fps)

            # ── Display ──────────────────────────────────────────
            cv2.imshow(window_name, frame)

            # ── Key handling ─────────────────────────────────────
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q") or key == 27:  # Q or ESC
                console.print("\n[dim]👋 Webcam closed.[/]")
                break

            elif key == ord(" "):  # SPACE — capture and run pipeline
                if num_faces == 0:
                    console.print(
                        "[yellow]⚠  No face detected in frame — "
                        "position your face and try again.[/]"
                    )
                    continue

                capture_count += 1

                # Show "processing" overlay
                _draw_hud(frame, num_faces, fps, processing=True)
                cv2.imshow(window_name, frame)
                cv2.waitKey(1)  # Force display update

                # Save frame to temp file
                tmp_dir = tempfile.gettempdir()
                capture_path = os.path.join(tmp_dir, f"webcam_capture_{capture_count}.jpg")
                cv2.imwrite(capture_path, frame)

                console.print(
                    f"\n[bold bright_cyan]📸 Captured frame #{capture_count}[/]"
                    f" → {capture_path}"
                )

                # Run the full pipeline
                try:
                    from .pipeline import run as run_pipeline
                    results = run_pipeline(
                        image_path=capture_path,
                        model=model,
                        verbose=verbose,
                    )
                    console.print(
                        f"\n[bold green]✓ Pipeline complete for capture #{capture_count}[/]"
                        "\n   Resuming live webcam…\n"
                    )
                except Exception as e:
                    console.print(
                        f"\n[bold red]❌ Pipeline error:[/] {e}"
                        "\n   Resuming live webcam…\n"
                    )

    except KeyboardInterrupt:
        console.print("\n\n[dim]⛔ Interrupted by user.[/]")

    finally:
        cap.release()
        cv2.destroyAllWindows()
        console.print("[dim]Camera released.[/]")
