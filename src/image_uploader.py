"""
image_uploader.py — Stage 2: Upload the cropped face to ImgBB for a public URL.

SerpAPI's Google Lens engine requires a publicly accessible image URL.
ImgBB provides free image hosting with a simple REST API.
"""

import base64
import os

import requests

from .utils import console


IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload"


def upload_image(image_path: str, api_key: str) -> str:
    """
    Upload a local image to ImgBB and return the public URL.

    Parameters
    ----------
    image_path : str
        Path to the local image file (JPEG/PNG).
    api_key : str
        ImgBB API key.

    Returns
    -------
    str — Public URL of the uploaded image.

    Raises
    ------
    FileNotFoundError — if image file doesn't exist
    RuntimeError      — if the upload fails
    """
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    console.print(f"\n[bold cyan]☁️  Stage 2:[/] Image Upload (ImgBB)")
    console.print(f"   File: {image_path}")

    # Read and base64-encode the image
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "key": api_key,
        "image": image_data,
        "name": "face_scan_query",
    }

    console.print("   Uploading…")
    response = requests.post(IMGBB_UPLOAD_URL, data=payload, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(
            f"ImgBB upload failed (HTTP {response.status_code}): "
            f"{response.text[:300]}"
        )

    result = response.json()

    if not result.get("success"):
        raise RuntimeError(f"ImgBB upload failed: {result}")

    public_url = result["data"]["url"]
    display_url = result["data"].get("display_url", public_url)
    delete_url = result["data"].get("delete_url", "N/A")

    console.print(f"   [bold green]✓[/] Uploaded successfully!")
    console.print(f"   Public URL : {public_url}")
    console.print(f"   Delete URL : {delete_url}")

    return public_url
