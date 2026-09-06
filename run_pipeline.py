#!/usr/bin/env python3
"""
run_pipeline.py — CLI entry point for the Face ID + Blockchain Verification pipeline.

Usage:
    python run_pipeline.py --image path/to/photo.jpg
    python run_pipeline.py --image photo.jpg --model cnn --verbose
"""

import argparse
import sys
import json

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Face ID + Blockchain Verification Pipeline\n"
            "HH Goa 2026 — Task 3\n\n"
            "Detects a face from an input image (or live webcam), searches for\n"
            "matching social media posts, and records the match on the blockchain."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Input source: --image or --webcam (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--image", "-i",
        help="Path to the input image containing a face.",
    )
    input_group.add_argument(
        "--webcam", "-w",
        action="store_true",
        help="Launch live webcam mode with real-time face detection.",
    )

    parser.add_argument(
        "--model", "-m",
        choices=["dnn", "haar"],
        default="dnn",
        help="Face detection model: 'dnn' (accurate, default) or 'haar' (fast).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose/debug output.",
    )
    parser.add_argument(
        "--output", "-o",
        help="Optional: save full pipeline results to a JSON file.",
    )

    args = parser.parse_args()

    # ── Webcam mode ──────────────────────────────────────────────
    if args.webcam:
        try:
            from src.webcam import run_webcam
        except ImportError as e:
            print(
                f"\n❌ Import error: {e}\n"
                f"Make sure you've installed dependencies:\n"
                f"   pip install -r requirements.txt\n"
            )
            sys.exit(1)

        try:
            run_webcam(model=args.model, verbose=args.verbose)
        except KeyboardInterrupt:
            print("\n\n⛔ Webcam interrupted by user.")
            sys.exit(130)
        except Exception as e:
            print(f"\n❌ Webcam error: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)
        return

    # ── Image mode (original behavior) ───────────────────────────
    try:
        from src.pipeline import run
    except ImportError as e:
        print(
            f"\n❌ Import error: {e}\n"
            f"Make sure you've installed dependencies:\n"
            f"   pip install -r requirements.txt\n"
        )
        sys.exit(1)

    try:
        results = run(
            image_path=args.image,
            model=args.model,
            verbose=args.verbose,
        )

        # Optionally save results
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n📁 Results saved to: {args.output}")

    except FileNotFoundError as e:
        print(f"\n❌ File not found: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n❌ {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"\n❌ Pipeline error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⛔ Pipeline interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
