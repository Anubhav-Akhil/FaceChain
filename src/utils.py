"""
utils.py — Shared helpers: hashing, logging, config loading.
"""

import hashlib
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(legacy_windows=False)


# ──────────────────────────────────────────────
#  Config
# ──────────────────────────────────────────────

def load_config() -> dict:
    """Load environment variables from .env and return them as a dict."""
    # Try .env in project root (two levels up from this file)
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"

    if not env_path.exists():
        console.print(
            "[bold red]ERROR:[/] .env file not found. "
            "Copy .env.example → .env and fill in your API keys."
        )
        sys.exit(1)

    load_dotenv(env_path)

    required_keys = [
        "SERPAPI_KEY",
        "IMGBB_API_KEY",
        "ALCHEMY_RPC_URL",
        "PRIVATE_KEY",
    ]

    config = {}
    missing = []
    for key in required_keys:
        val = os.getenv(key, "").strip()
        if not val or val.startswith("your_"):
            missing.append(key)
        config[key] = val

    # CONTRACT_ADDRESS is optional (may not be deployed yet)
    config["CONTRACT_ADDRESS"] = os.getenv("CONTRACT_ADDRESS", "").strip()

    if missing:
        console.print(
            f"[bold red]ERROR:[/] Missing or placeholder values for: "
            f"{', '.join(missing)}\n"
            f"Edit your .env file with real API keys."
        )
        sys.exit(1)

    return config


# ──────────────────────────────────────────────
#  Hashing
# ──────────────────────────────────────────────

def compute_data_hash(match_data: dict) -> str:
    """
    Compute a deterministic SHA-256 hash of the match data dict.

    The dict is serialized with sorted keys so the hash is reproducible.
    Returns the hex-encoded hash string (64 chars).
    """
    serialized = json.dumps(match_data, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def hex_to_bytes32(hex_str: str) -> bytes:
    """Convert a 64-char hex hash string to a 32-byte value for Solidity bytes32."""
    clean = hex_str.replace("0x", "")
    return bytes.fromhex(clean)


# ──────────────────────────────────────────────
#  Logging
# ──────────────────────────────────────────────

def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure and return a Rich-powered logger."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=console)],
    )

    logger = logging.getLogger("faceid_pipeline")
    logger.setLevel(level)
    return logger
