"""
pipeline.py — Main orchestrator that runs the full Face ID + Blockchain pipeline.

Flow:
  1. Detect & encode face from input image
  2. Upload cropped face to ImgBB
  3. Reverse image search via Google Lens (SerpAPI)
  4. Register match data on Ethereum Sepolia blockchain
  5. Verify the on-chain record
"""

import json
import time
from datetime import datetime, timezone

from rich.panel import Panel
from rich.table import Table

from .blockchain import BlockchainClient
from .face_detector import detect_and_encode
from .image_uploader import upload_image
from .reverse_search import search_face
from .utils import compute_data_hash, console, load_config, setup_logging


def run(image_path: str, model: str = "dnn", verbose: bool = False) -> dict:
    """
    Execute the full Face ID → Search → Blockchain pipeline.

    Parameters
    ----------
    image_path : str
        Path to the input image containing a face.
    model : str
        Face detection model — "dnn" (accurate) or "haar" (fast).
    verbose : bool
        Enable debug-level logging.

    Returns
    -------
    dict — Complete pipeline results with all stage outputs.
    """
    logger = setup_logging(verbose)
    start_time = time.time()

    # ── Header ───────────────────────────────────────────────────
    console.print(
        Panel(
            "[bold white]Face ID + Blockchain Verification Pipeline[/]\n"
            "[dim]HH Goa 2026 — Task 3[/]",
            border_style="bright_cyan",
            padding=(1, 2),
        )
    )

    # ── Load config ──────────────────────────────────────────────
    config = load_config()

    results = {
        "input_image": image_path,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stages": {},
    }

    # ═══════════════════════════════════════════════════════════
    #  STAGE 1 — Face Detection & Encoding
    # ═══════════════════════════════════════════════════════════
    face_data = detect_and_encode(image_path, model=model)
    results["stages"]["face_detection"] = {
        "num_faces": face_data["num_faces"],
        "face_location": face_data["face_location"],
        "encoding_dims": len(face_data["encoding"]),
        "cropped_path": face_data["cropped_path"],
    }

    # ═══════════════════════════════════════════════════════════
    #  STAGE 2 — Upload to ImgBB
    # ═══════════════════════════════════════════════════════════
    public_url = upload_image(
        face_data["cropped_path"],
        api_key=config["IMGBB_API_KEY"],
    )
    results["stages"]["image_upload"] = {"public_url": public_url}

    # ═══════════════════════════════════════════════════════════
    #  STAGE 3 — Reverse Image Search
    # ═══════════════════════════════════════════════════════════
    match_data = search_face(
        image_url=public_url,
        api_key=config["SERPAPI_KEY"],
    )
    results["stages"]["reverse_search"] = {
        "title": match_data.get("title"),
        "link": match_data.get("link"),
        "source": match_data.get("source"),
        "is_social_media": match_data.get("is_social"),
        "total_matches": len(match_data.get("all_matches", [])),
    }

    # ═══════════════════════════════════════════════════════════
    #  STAGE 4 — Blockchain Registration
    # ═══════════════════════════════════════════════════════════
    contract_address = config.get("CONTRACT_ADDRESS", "")
    if not contract_address:
        console.print(
            "\n[bold yellow]⚠  CONTRACT_ADDRESS not set in .env[/]\n"
            "   Run [bold]python deploy_contract.py[/] first to deploy the contract.\n"
            "   Skipping blockchain stages."
        )
        results["stages"]["blockchain"] = {"skipped": True, "reason": "No contract deployed"}
        results["stages"]["verification"] = {"skipped": True}
    else:
        blockchain = BlockchainClient(
            rpc_url=config["ALCHEMY_RPC_URL"],
            private_key=config["PRIVATE_KEY"],
            contract_address=contract_address,
        )

        # Register
        tx_result = blockchain.register_match(
            match_data=match_data,
            image_url=public_url,
        )
        results["stages"]["blockchain"] = tx_result

        # ═══════════════════════════════════════════════════════
        #  STAGE 5 — On-Chain Verification
        # ═══════════════════════════════════════════════════════
        verification = blockchain.verify_match(tx_result["data_hash"])
        results["stages"]["verification"] = verification

    # ── Summary ──────────────────────────────────────────────────
    elapsed = time.time() - start_time
    results["elapsed_seconds"] = round(elapsed, 2)

    _print_summary(results)

    return results


def _print_summary(results: dict):
    """Print a rich summary table of the pipeline results."""
    console.print("\n")

    table = Table(
        title="📋 Pipeline Summary",
        show_header=True,
        header_style="bold cyan",
        border_style="bright_cyan",
        padding=(0, 1),
    )
    table.add_column("Stage", style="bold white", min_width=20)
    table.add_column("Status", min_width=10)
    table.add_column("Details", min_width=40)

    stages = results.get("stages", {})

    # Face Detection
    fd = stages.get("face_detection", {})
    table.add_row(
        "🧠 Face Detection",
        "[green]✓ Done[/]",
        f"{fd.get('num_faces', 0)} face(s), {fd.get('encoding_dims', 0)}-d encoding",
    )

    # Image Upload
    iu = stages.get("image_upload", {})
    table.add_row(
        "☁️  Image Upload",
        "[green]✓ Done[/]",
        f"{iu.get('public_url', 'N/A')[:60]}…",
    )

    # Reverse Search
    rs = stages.get("reverse_search", {})
    social_tag = "🟢 Social" if rs.get("is_social_media") else "🟡 Web"
    table.add_row(
        "🔍 Reverse Search",
        "[green]✓ Done[/]",
        f"{social_tag} | {rs.get('source', 'N/A')} | "
        f"{rs.get('total_matches', 0)} total matches",
    )

    # Blockchain
    bc = stages.get("blockchain", {})
    if bc.get("skipped"):
        table.add_row(
            "⛓️  Blockchain",
            "[yellow]⚠ Skipped[/]",
            bc.get("reason", ""),
        )
    else:
        table.add_row(
            "⛓️  Blockchain",
            "[green]✓ Done[/]",
            f"Block #{bc.get('block', '?')} | Gas: {bc.get('gas_used', '?')}",
        )

    # Verification
    vf = stages.get("verification", {})
    if vf.get("skipped"):
        table.add_row("✅ Verification", "[yellow]⚠ Skipped[/]", "")
    elif vf.get("verified"):
        table.add_row(
            "✅ Verification",
            "[green]✓ Verified[/]",
            "On-chain hash matches local data",
        )
    else:
        table.add_row("✅ Verification", "[red]✗ Failed[/]", "Hash mismatch!")

    console.print(table)

    # Transaction links
    if not bc.get("skipped") and bc.get("etherscan"):
        console.print(
            f"\n   🔗 View on Etherscan: [link={bc['etherscan']}]{bc['etherscan']}[/link]"
        )
    if not bc.get("skipped") and bc.get("tx_hash"):
        console.print(f"   🔑 Tx Hash: 0x{bc['tx_hash']}")
    if not bc.get("skipped") and bc.get("data_hash"):
        console.print(f"   #️⃣  Data Hash: 0x{bc['data_hash']}")

    console.print(f"\n   ⏱️  Total time: {results.get('elapsed_seconds', '?')}s\n")


def run_with_progress(
    image_path: str,
    model: str = "dnn",
    verbose: bool = False,
    on_progress=None,
) -> dict:
    """
    Execute the full pipeline with real-time progress callbacks for the web UI.

    Parameters
    ----------
    image_path : str
        Path to the input image containing a face.
    model : str
        Face detection model — "dnn" or "haar".
    verbose : bool
        Enable debug-level logging.
    on_progress : callable, optional
        Callback: on_progress(stage: str, status: str, data: dict)
        status is one of: "running", "done", "error", "skipped"

    Returns
    -------
    dict — Complete pipeline results with all stage outputs.
    """
    logger = setup_logging(verbose)
    start_time = time.time()

    def _emit(stage, status, data=None):
        if on_progress:
            on_progress(stage, status, data or {})

    config = load_config()

    results = {
        "input_image": image_path,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stages": {},
    }

    # ═══════════════════════════════════════════════════════════
    #  STAGE 1 — Face Detection & Encoding
    # ═══════════════════════════════════════════════════════════
    _emit("face_detection", "running", {"message": "Detecting faces in image…"})
    try:
        face_data = detect_and_encode(image_path, model=model)
        stage_result = {
            "num_faces": face_data["num_faces"],
            "face_location": face_data["face_location"],
            "encoding_dims": len(face_data["encoding"]),
            "cropped_path": face_data["cropped_path"],
        }
        results["stages"]["face_detection"] = stage_result
        _emit("face_detection", "done", stage_result)
    except Exception as e:
        _emit("face_detection", "error", {"error": str(e)})
        raise

    # ═══════════════════════════════════════════════════════════
    #  STAGE 2 — Upload to ImgBB
    # ═══════════════════════════════════════════════════════════
    _emit("image_upload", "running", {"message": "Uploading face crop to ImgBB…"})
    try:
        public_url = upload_image(
            face_data["cropped_path"],
            api_key=config["IMGBB_API_KEY"],
        )
        stage_result = {"public_url": public_url}
        results["stages"]["image_upload"] = stage_result
        _emit("image_upload", "done", stage_result)
    except Exception as e:
        _emit("image_upload", "error", {"error": str(e)})
        raise

    # ═══════════════════════════════════════════════════════════
    #  STAGE 3 — Reverse Image Search
    # ═══════════════════════════════════════════════════════════
    _emit("reverse_search", "running", {"message": "Searching Google Lens for matches…"})
    try:
        match_data = search_face(
            image_url=public_url,
            api_key=config["SERPAPI_KEY"],
        )
        # Build a clean copy of all_matches to avoid circular references
        # (the best match dict has an 'all_matches' key pointing back at itself)
        raw_matches = match_data.get("all_matches", [])
        clean_matches = [
            {
                "title": m.get("title", "Untitled"),
                "link": m.get("link", ""),
                "source": m.get("source", ""),
                "thumbnail": m.get("thumbnail", ""),
                "snippet": m.get("snippet", ""),
            }
            for m in raw_matches
        ]

        stage_result = {
            "title": match_data.get("title"),
            "link": match_data.get("link"),
            "source": match_data.get("source"),
            "thumbnail": match_data.get("thumbnail", ""),
            "snippet": match_data.get("snippet", ""),
            "is_social_media": match_data.get("is_social"),
            "total_matches": len(clean_matches),
            "all_matches": clean_matches,
        }
        results["stages"]["reverse_search"] = stage_result
        _emit("reverse_search", "done", stage_result)
    except Exception as e:
        _emit("reverse_search", "error", {"error": str(e)})
        raise

    # ═══════════════════════════════════════════════════════════
    #  STAGE 4 — Blockchain Registration
    # ═══════════════════════════════════════════════════════════
    contract_address = config.get("CONTRACT_ADDRESS", "")
    if not contract_address:
        skip_data = {"skipped": True, "reason": "No contract deployed"}
        results["stages"]["blockchain"] = skip_data
        results["stages"]["verification"] = {"skipped": True}
        _emit("blockchain", "skipped", skip_data)
        _emit("verification", "skipped", {"skipped": True})
    else:
        _emit("blockchain", "running", {"message": "Registering match on Ethereum Sepolia…"})
        try:
            blockchain = BlockchainClient(
                rpc_url=config["ALCHEMY_RPC_URL"],
                private_key=config["PRIVATE_KEY"],
                contract_address=contract_address,
            )

            tx_result = blockchain.register_match(
                match_data=match_data,
                image_url=public_url,
            )
            results["stages"]["blockchain"] = tx_result
            _emit("blockchain", "done", tx_result)
        except Exception as e:
            _emit("blockchain", "error", {"error": str(e)})
            raise

        # ═══════════════════════════════════════════════════════
        #  STAGE 5 — On-Chain Verification
        # ═══════════════════════════════════════════════════════
        _emit("verification", "running", {"message": "Verifying on-chain record…"})
        try:
            verification = blockchain.verify_match(tx_result["data_hash"])
            results["stages"]["verification"] = verification
            _emit("verification", "done", verification)
        except Exception as e:
            _emit("verification", "error", {"error": str(e)})
            raise

    # ── Summary ──────────────────────────────────────────────────
    elapsed = time.time() - start_time
    results["elapsed_seconds"] = round(elapsed, 2)
    _emit("complete", "done", {"elapsed_seconds": results["elapsed_seconds"]})

    return results

