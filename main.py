import sys
import argparse
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

def main():
    import multiprocessing
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(
        description="JAJCE (Just Another JPEG Conversion Engine) - High performance JPEG XL bulk converter and AI auto-tagger."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        help="Input image files or directories to convert (if omitted, launches GUI)."
    )
    parser.add_argument(
        "--mode",
        choices=["lossless", "lossy"],
        default="lossless",
        help="Conversion mode: 'lossless' (reversible JPEG transcoding) or 'lossy' (fresh compression)."
    )
    parser.add_argument(
        "--distance", "-d",
        type=float,
        default=1.0,
        help="Target Butteraugli visual distance for lossy mode (default: 1.0, visually lossless)."
    )
    parser.add_argument(
        "--effort", "-e",
        type=int,
        default=7,
        help="Encoder effort 1-9 (default: 7)."
    )
    parser.add_argument(
        "--tag",
        action="store_true",
        help="Enable AI auto-tagging with SmolVLM-256M-Instruct."
    )
    parser.add_argument(
        "--out-dir", "-o",
        type=str,
        default=None,
        help="Destination directory for output .jxl files."
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Force launch graphical interface."
    )

    args = parser.parse_args()

    # If no inputs provided or --gui flag passed, launch the GUI
    if not args.inputs or args.gui:
        from jajce.app import run_app
        run_app()
    else:
        # CLI Batch execution
        from jajce.engine.converter import ImageConverter, ConversionOptions
        from jajce.vlm.tagger import SmolVLMTagger

        options = ConversionOptions(
            mode=args.mode,
            distance=args.distance,
            effort=args.effort,
            enable_ai_tagging=args.tag,
            output_dir=args.out_dir
        )

        converter = ImageConverter()
        tagger = SmolVLMTagger.get_instance() if args.tag else None
        if tagger:
            print("Initializing SmolVLM-256M-Instruct...")
            tagger.load_model(status_callback=print)

        for in_file in args.inputs:
            p = Path(in_file)
            if not p.exists():
                print(f"Skipping: {in_file} (not found)")
                continue

            tags = []
            if tagger:
                print(f"Tagging {p.name} with SmolVLM...")
                tags = tagger.tag_image(str(p))
                print(f"  Identified tags: {tags}")

            print(f"Converting {p.name} -> .jxl ({args.mode})...")
            res = converter.convert_image(str(p), options=options, tags=tags)
            if res.success:
                print(f"  Success: {res.output_path} ({res.original_size} -> {res.converted_size} bytes, saved {res.compression_ratio:.1f}%)")
            else:
                print(f"  Failed: {res.error_message}")

if __name__ == "__main__":
    main()
