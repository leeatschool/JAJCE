import time
from typing import List, Dict, Optional
from PySide6.QtCore import QThread, Signal

from jajce.engine.converter import ImageConverter, ConversionOptions, ConversionResult
from jajce.vlm.tagger import SmolVLMTagger

class BatchWorker(QThread):
    """
    Background worker thread that handles batch image tagging and conversion
    without blocking the PySide6 UI.
    """
    item_started = Signal(str, str)             # input_path, status_text
    item_progress = Signal(str, str)            # input_path, detail_text
    item_tagged = Signal(str, list)             # input_path, list_of_tags
    item_finished = Signal(str, object)         # input_path, ConversionResult
    batch_progress = Signal(int, int, float)    # completed_items, total_items, percent
    batch_finished = Signal(int, int)           # success_count, error_count
    log_message = Signal(str)                   # log text

    def __init__(self, items: List[str], options: ConversionOptions, item_tags: Optional[Dict[str, List[str]]] = None):
        super().__init__()
        self.items = items
        self.options = options
        self.item_tags = item_tags or {}
        self.converter = ImageConverter()
        self._is_cancelled = False
        self._is_paused = False

    def cancel(self):
        self._is_cancelled = True

    def pause(self):
        self._is_paused = True

    def resume(self):
        self._is_paused = False

    def run(self):
        total = len(self.items)
        success_count = 0
        error_count = 0

        self.log_message.emit(f"Starting batch conversion for {total} files (Mode: {self.options.mode.upper()})...")

        # Pre-load SmolVLM if tagging is enabled
        tagger = None
        if self.options.enable_ai_tagging:
            self.log_message.emit("Initializing SmolVLM-256M-Instruct for auto-tagging...")
            tagger = SmolVLMTagger.get_instance()
            tagger.load_model(status_callback=lambda msg: self.log_message.emit(f"[SmolVLM] {msg}"))

        for idx, path_str in enumerate(self.items):
            while self._is_paused and not self._is_cancelled:
                time.sleep(0.2)

            if self._is_cancelled:
                self.log_message.emit("Batch conversion cancelled by user.")
                break

            self.item_started.emit(path_str, "Processing...")
            self.log_message.emit(f"Processing ({idx+1}/{total}): {path_str}")

            # 1. AI Tagging (if enabled and no manual tags were already set)
            tags = list(self.item_tags.get(path_str, []))
            if self.options.enable_ai_tagging and tagger:
                self.item_progress.emit(path_str, "Identifying items via SmolVLM...")
                try:
                    generated_tags = tagger.tag_image(
                        path_str,
                        custom_prompt=self.options.ai_prompt,
                        max_tags=self.options.max_tags,
                        status_callback=lambda msg: self.log_message.emit(f"[SmolVLM] {msg}")
                    )
                    # Merge unique tags
                    for t in generated_tags:
                        if t not in tags:
                            tags.append(t)
                    self.item_tagged.emit(path_str, tags)
                    self.log_message.emit(f"Identified tags for {path_str}: {tags}")
                except Exception as e:
                    self.log_message.emit(f"Warning: Tagging error on {path_str}: {e}")

            # 2. Conversion
            self.item_progress.emit(path_str, "Encoding to .jxl...")
            result = self.converter.convert_image(
                path_str,
                options=self.options,
                tags=tags,
                progress_callback=lambda msg: self.item_progress.emit(path_str, msg)
            )

            if result.success:
                success_count += 1
                self.log_message.emit(
                    f"Converted: {result.output_path} | "
                    f"Saved: {result.compression_ratio:+.1f}% | "
                    f"Tags: {len(result.tags)}"
                )
            else:
                error_count += 1
                self.log_message.emit(f"Error converting {path_str}: {result.error_message}")

            self.item_finished.emit(path_str, result)
            pct = ((idx + 1) / total) * 100.0
            self.batch_progress.emit(idx + 1, total, pct)

        self.batch_finished.emit(success_count, error_count)
        self.log_message.emit(
            f"Batch completed: {success_count} succeeded, {error_count} failed out of {total} items."
        )
