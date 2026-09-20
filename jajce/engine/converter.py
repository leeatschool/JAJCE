import os
import sys
import tempfile
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict, Any
from PIL import Image

from jajce.engine.jxl_bin import JXLBinaries
from jajce.engine.metadata import MetadataManager

SUPPORTED_EXTENSIONS = {
    # JPEG
    ".jpg", ".jpeg", ".jpe", ".jfif",
    # PNG & Animated PNG
    ".png", ".apng",
    # WebP
    ".webp",
    # GIF
    ".gif",
    # BMP & DIB
    ".bmp", ".dib",
    # TIFF
    ".tif", ".tiff",
    # AVIF
    ".avif", ".avifs",
    # TGA
    ".tga",
    # NetPBM
    ".ppm", ".pgm", ".pnm", ".pam", ".pfm",
    # Icons
    ".ico", ".cur",
    # QOI
    ".qoi"
}

NATIVE_CJXL_EXTENSIONS = {
    ".jpg", ".jpeg", ".jpe", ".jfif",
    ".png", ".apng",
    ".gif",
    ".ppm", ".pgm", ".pnm", ".pam", ".pfm", ".pgx"
}

@dataclass
class ConversionOptions:
    mode: str = "lossless"  # "lossless" (reversible) or "lossy" (fresh compression)
    quality: int = 85       # 0 - 100 (for lossy mode)
    distance: float = 1.0   # 0.0 - 15.0 (1.0 = visually lossless)
    use_distance: bool = True  # If True use distance, else quality
    effort: int = 7         # 1 - 9
    progressive: bool = False
    enable_ai_tagging: bool = False
    ai_prompt: Optional[str] = None
    max_tags: int = 8
    overwrite_existing: bool = True
    output_dir: Optional[str] = None

@dataclass
class ConversionResult:
    input_path: str
    output_path: str
    success: bool
    original_size: int = 0
    converted_size: int = 0
    compression_ratio: float = 0.0
    tags: List[str] = field(default_factory=list)
    error_message: Optional[str] = None

class ImageConverter:
    """
    Core engine for converting a wide variety of images into .jxl format
    with reversible lossless transcoding or fresh lossy recompression.
    """

    def __init__(self):
        self.binaries = JXLBinaries.get_all()
        self.cjxl = self.binaries.get("cjxl")

    def is_supported(self, file_path: str) -> bool:
        ext = Path(file_path).suffix.lower()
        return ext in SUPPORTED_EXTENSIONS

    def get_output_path(self, input_path: str, output_dir: Optional[str] = None) -> str:
        in_p = Path(input_path)
        out_directory = Path(output_dir) if output_dir else in_p.parent
        return str(out_directory / f"{in_p.stem}.jxl")

    def convert_image(
        self,
        input_path: str,
        options: Optional[ConversionOptions] = None,
        tags: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> ConversionResult:
        if options is None:
            options = ConversionOptions()

        in_p = Path(input_path)
        if not in_p.exists():
            return ConversionResult(
                input_path=input_path,
                output_path="",
                success=False,
                error_message=f"File not found: {input_path}"
            )

        cjxl_bin = self.cjxl or JXLBinaries.find_binary("cjxl")
        if not cjxl_bin:
            return ConversionResult(
                input_path=input_path,
                output_path="",
                success=False,
                error_message="cjxl encoder binary not found. Please install libjxl."
            )

        original_size = in_p.stat().st_size
        out_p = Path(self.get_output_path(input_path, options.output_dir))
        out_p.parent.mkdir(parents=True, exist_ok=True)

        if out_p.exists() and not options.overwrite_existing:
            return ConversionResult(
                input_path=input_path,
                output_path=str(out_p),
                success=False,
                original_size=original_size,
                error_message="Output file already exists and overwrite is disabled."
            )

        ext = in_p.suffix.lower()
        is_jpeg = ext in {".jpg", ".jpeg", ".jpe", ".jfif"}
        temp_input_file = None

        try:
            # Check if format needs intermediate conversion to PNG for cjxl
            actual_input = str(in_p)
            if ext not in NATIVE_CJXL_EXTENSIONS:
                if progress_callback:
                    progress_callback("Normalizing image format via Pillow...")
                with Image.open(in_p) as pil_img:
                    # Create temporary PNG
                    temp_dir = tempfile.gettempdir()
                    temp_input_file = os.path.join(temp_dir, f"jajce_temp_{os.getpid()}_{in_p.stem}.png")
                    # Preserve transparency if available
                    if pil_img.mode in ("RGBA", "LA") or (pil_img.mode == "P" and "transparency" in pil_img.info):
                        pil_img.convert("RGBA").save(temp_input_file, format="PNG")
                    else:
                        pil_img.convert("RGB").save(temp_input_file, format="PNG")
                    actual_input = temp_input_file

            # Build cjxl command
            cmd = [cjxl_bin, actual_input, str(out_p)]

            # Always ensure container format is used so metadata boxes can be stored
            cmd.extend(["--container=1"])

            # Mode selection
            if options.mode == "lossless":
                if is_jpeg and ext in NATIVE_CJXL_EXTENSIONS:
                    # Lossless Reversible JPEG Transcoding
                    cmd.extend(["-j", "1", "--lossless_jpeg=1", "--allow_jpeg_reconstruction=1"])
                else:
                    # Mathematically lossless for other formats
                    cmd.extend(["-d", "0"])
            else:
                # Lossy Re-encoding ("Fresh" compression)
                if is_jpeg:
                    # Force decoding to pixels and re-encoding with fresh compression
                    cmd.extend(["-j", "0"])

                if options.use_distance:
                    cmd.extend(["-d", str(options.distance)])
                else:
                    cmd.extend(["-q", str(options.quality)])

            # Effort
            cmd.extend(["-e", str(options.effort)])

            # Progressive mode
            if options.progressive:
                cmd.append("-p")

            # Quiet output
            cmd.append("--quiet")

            if progress_callback:
                progress_callback("Encoding to JPEG XL (.jxl)...")

            # Execute cjxl
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=flags,
                timeout=120
            )

            if proc.returncode != 0:
                err_msg = proc.stderr.strip() or f"cjxl exited with code {proc.returncode}"
                return ConversionResult(
                    input_path=input_path,
                    output_path=str(out_p),
                    success=False,
                    original_size=original_size,
                    error_message=err_msg
                )

            # Inject Tags / Metadata if provided
            final_tags = list(tags) if tags else []
            if final_tags:
                if progress_callback:
                    progress_callback("Injecting tags into .jxl container...")
                MetadataManager.inject_metadata_to_jxl(str(out_p), final_tags)

            converted_size = out_p.stat().st_size
            ratio = ((original_size - converted_size) / original_size * 100.0) if original_size > 0 else 0.0

            return ConversionResult(
                input_path=input_path,
                output_path=str(out_p),
                success=True,
                original_size=original_size,
                converted_size=converted_size,
                compression_ratio=ratio,
                tags=final_tags
            )

        except Exception as e:
            return ConversionResult(
                input_path=input_path,
                output_path=str(out_p),
                success=False,
                original_size=original_size,
                error_message=str(e)
            )
        finally:
            if temp_input_file and os.path.exists(temp_input_file):
                try:
                    os.remove(temp_input_file)
                except Exception:
                    pass
