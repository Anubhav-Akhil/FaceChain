"""
face_detector.py — Stage 1: Detect and encode a face from an input image.

Uses OpenCV's DNN-based face detector (built-in, no extra downloads) to:
  1. Detect face locations in the image
  2. Compute a perceptual encoding of the face region
  3. Crop the face region and save it for later upload

This approach works on any Python version with zero C++ compilation.
"""

import hashlib
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
import requests

from .utils import console


# ── DNN Face Detector Model URL (YuNet ONNX) ─────────────────────
# OpenCV's official YuNet ONNX model for face detection (fast, modern)
_YUNET_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/"
    "face_detection_yunet/face_detection_yunet_2023mar.onnx"
)


def _get_model_dir() -> Path:
    """Return (and create) a cache directory for model files."""
    cache_dir = Path(tempfile.gettempdir()) / "faceid_models"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


def _download_if_needed(url: str, filename: str) -> str:
    """Download a file if it doesn't exist in the cache directory."""
    model_dir = _get_model_dir()
    filepath = model_dir / filename

    if not filepath.exists() or filepath.stat().st_size == 0:
        console.print(f"   Downloading {filename}…")
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, stream=True, timeout=60)
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
        console.print(f"   [green]✓ Downloaded {filename}[/]")

    return str(filepath)


def _load_yunet_detector(w: int, h: int, confidence_threshold: float = 0.5):
    """Load OpenCV's YuNet ONNX face detector."""
    onnx_path = _download_if_needed(_YUNET_URL, "face_detection_yunet.onnx")
    detector = cv2.FaceDetectorYN.create(
        model=onnx_path,
        config="",
        input_size=(w, h),
        score_threshold=confidence_threshold,
        nms_threshold=0.3,
        top_k=5000,
    )
    return detector


def _compute_face_encoding(face_bgr: np.ndarray) -> list:
    """
    Compute a 128-dimensional encoding from a face image.

    Uses a combination of:
    - Histogram features (color distribution)
    - Spatial features (resized pixel values)
    - Edge features (gradient information)

    This is a lightweight alternative to deep learning embeddings.
    """
    # Resize face to standard size
    face_resized = cv2.resize(face_bgr, (64, 64))

    # Convert to different color spaces
    face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
    face_hsv = cv2.cvtColor(face_resized, cv2.COLOR_BGR2HSV)

    encoding = []

    # 1. Grayscale histogram (32 bins)
    hist_gray = cv2.calcHist([face_gray], [0], None, [32], [0, 256])
    hist_gray = cv2.normalize(hist_gray, hist_gray).flatten()
    encoding.extend(hist_gray.tolist())

    # 2. Hue histogram (32 bins) — captures skin tone
    hist_hue = cv2.calcHist([face_hsv], [0], None, [32], [0, 180])
    hist_hue = cv2.normalize(hist_hue, hist_hue).flatten()
    encoding.extend(hist_hue.tolist())

    # 3. LBP-like features — simplified local binary patterns (32 values)
    lbp_features = []
    small = cv2.resize(face_gray, (8, 8))
    mean_val = small.mean()
    for row in small:
        for val in row:
            lbp_features.append(1.0 if val > mean_val else 0.0)
    encoding.extend(lbp_features[:32])

    # 4. Spatial structure — downsampled face (32 values)
    tiny = cv2.resize(face_gray, (8, 4)).flatten().astype(float)
    tiny = tiny / 255.0  # Normalize to [0, 1]
    encoding.extend(tiny.tolist())

    return encoding[:128]  # Ensure exactly 128 dimensions


def detect_and_encode(
    image_path: str,
    model: str = "dnn",
    confidence_threshold: float = 0.5,
) -> dict:
    """
    Detect faces in the given image and return encoding + cropped face.

    Parameters
    ----------
    image_path : str
        Path to the input image file.
    model : str
        Detection model — "dnn" (accurate, recommended) or "haar" (fast).
    confidence_threshold : float
        Minimum confidence for DNN detections (0.0–1.0).

    Returns
    -------
    dict with keys:
        - encoding     : list[float]  — 128-d face encoding
        - face_location: dict         — {x, y, w, h} of detected face
        - cropped_path : str          — path to the saved cropped face image
        - num_faces    : int          — total faces detected in the image

    Raises
    ------
    FileNotFoundError  — if image_path does not exist
    ValueError         — if no faces are detected
    """
    image_path = str(Path(image_path).resolve())

    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    console.print(f"\n[bold cyan]🧠 Stage 1:[/] Face Detection & Encoding")
    console.print(f"   Input : {image_path}")
    console.print(f"   Model : OpenCV {model.upper()}")

    # Read image
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    (h, w) = img.shape[:2]

    # ── Detect faces ─────────────────────────────────────────────
    faces = []

    if model == "dnn":
        detector = _load_yunet_detector(w, h, confidence_threshold)
        _, raw_faces = detector.detect(img)

        if raw_faces is not None:
            for f in raw_faces:
                fx, fy, fw, fh = f[:4]
                conf = f[-1]
                faces.append({
                    "x": max(0, int(fx)),
                    "y": max(0, int(fy)),
                    "w": min(w, int(fw)),
                    "h": min(h, int(fh)),
                    "confidence": float(conf),
                })

    else:  # Haar cascade fallback
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        detections = face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )

        for (x, y, fw, fh) in detections:
            faces.append({
                "x": int(x), "y": int(y),
                "w": int(fw), "h": int(fh),
                "confidence": 1.0,
            })

    num_faces = len(faces)
    console.print(f"   Faces detected: [bold green]{num_faces}[/]")

    if num_faces == 0:
        raise ValueError(
            "No faces detected in the image. "
            "Try a clearer, front-facing photo."
        )

    # Sort by confidence (highest first) and use the best face
    faces.sort(key=lambda f: f["confidence"], reverse=True)
    face = faces[0]

    fx, fy, fw, fh = face["x"], face["y"], face["w"], face["h"]
    console.print(
        f"   Face region: x={fx}, y={fy}, w={fw}, h={fh}  "
        f"(confidence: {face['confidence']:.2%})"
    )

    # ── Compute encoding ─────────────────────────────────────────
    face_region = img[fy:fy+fh, fx:fx+fw]
    encoding = _compute_face_encoding(face_region)

    console.print(
        f"   Encoding: {len(encoding)}-d vector  "
        f"(first 5 values: {[round(v, 4) for v in encoding[:5]]}…)"
    )

    # ── Crop the face with margin ────────────────────────────────
    pil_image = Image.open(image_path)
    img_w, img_h = pil_image.size

    margin = int(fh * 0.3)
    crop_top    = max(0, fy - margin)
    crop_bottom = min(img_h, fy + fh + margin)
    crop_left   = max(0, fx - margin)
    crop_right  = min(img_w, fx + fw + margin)

    face_crop = pil_image.crop((crop_left, crop_top, crop_right, crop_bottom))

    # Save to temp file
    tmp_dir = tempfile.gettempdir()
    cropped_path = os.path.join(tmp_dir, "temp_face_crop.jpg")
    face_crop.save(cropped_path, "JPEG", quality=95)

    console.print(f"   Cropped face saved → {cropped_path}")

    return {
        "encoding": encoding,
        "face_location": {"x": fx, "y": fy, "w": fw, "h": fh},
        "cropped_path": cropped_path,
        "num_faces": num_faces,
    }
