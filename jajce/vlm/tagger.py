import os
import re
import threading
from pathlib import Path
from typing import List, Optional, Callable
from PIL import Image

class SmolVLMTagger:
    """
    Manages lazy loading and image inference using HuggingFaceTB/SmolVLM-256M-Instruct
    to identify items in images and return clean tags.
    """
    _instance = None
    _lock = threading.Lock()

    def __init__(self, model_id: str = "HuggingFaceTB/SmolVLM-256M-Instruct"):
        self.model_id = model_id
        self.processor = None
        self.model = None
        self.is_loaded = False
        self.is_loading = False
        self.device = "cpu"

    @classmethod
    def get_instance(cls) -> "SmolVLMTagger":
        with cls._lock:
            if cls._instance is None:
                cls._instance = SmolVLMTagger()
            return cls._instance

    def load_model(self, status_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Loads processor and model weights into memory."""
        if self.is_loaded:
            return True

        with self._lock:
            if self.is_loaded:
                return True
            try:
                self.is_loading = True
                if status_callback:
                    status_callback("Loading PyTorch and Vision-Language Model...")

                import torch
                # Optimize CPU thread allocation
                cpu_threads = max(1, min(os.cpu_count() or 4, 8))
                torch.set_num_threads(cpu_threads)

                if torch.cuda.is_available():
                    self.device = "cuda"
                    dtype = torch.float16
                else:
                    self.device = "cpu"
                    dtype = torch.float32

                if status_callback:
                    status_callback("Initializing SmolVLM tokenizer & processor...")

                from transformers import AutoProcessor, AutoModelForImageTextToText

                self.processor = AutoProcessor.from_pretrained(self.model_id)
                if status_callback:
                    status_callback("Loading SmolVLM-256M-Instruct weights...")

                self.model = AutoModelForImageTextToText.from_pretrained(
                    self.model_id,
                    dtype=dtype,
                    low_cpu_mem_usage=True
                )
                self.model.to(self.device)
                self.model.eval()

                self.is_loaded = True
                self.is_loading = False
                if status_callback:
                    status_callback("SmolVLM model ready.")
                return True
            except Exception as e:
                self.is_loading = False
                if status_callback:
                    status_callback(f"Failed to load SmolVLM: {e}")
                return False

    def unload_model(self):
        """Unloads model to free RAM."""
        with self._lock:
            self.model = None
            self.processor = None
            self.is_loaded = False
            self.is_loading = False
            try:
                import gc
                gc.collect()
            except Exception:
                pass

    def extract_tags_from_text(self, text: str, max_tags: int = 8) -> List[str]:
        """Cleans and standardizes generated text into a list of concise tags."""
        if not text:
            return []

        # Remove common preamble phrases
        cleaned = re.sub(r"^(items|objects|tags|the image shows|this image contains|in this photo|we can see|identified items|depicted are|key objects:?)\s*:?", "", text, flags=re.IGNORECASE).strip()
        cleaned = cleaned.replace("\n", ", ").replace(";", ",")
        cleaned = re.sub(r"[\.!\?]", ", ", cleaned)

        # Split on commas
        raw_items = [item.strip() for item in cleaned.split(",") if item.strip()]

        # Filter stop words and punctuation
        stop_words = {
            "a", "an", "the", "and", "or", "in", "on", "at", "of", "with",
            "this", "that", "these", "those", "photo", "image", "picture",
            "combination", "focus", "primary", "background", "foreground",
            "element", "elements"
        }

        tags = []
        for raw in raw_items:
            # Remove leading bullet points, numbers, asterisks
            item = re.sub(r"^[\d\.\-\*\•\s]+", "", raw).strip().lower()
            if not item or item in stop_words or len(item) < 2 or len(item) > 35:
                continue

            # Check if this item is a sentence or contains stop phrases
            words = item.split()
            if len(words) > 4:
                # Truncate long multi-word explanations
                continue

            if item not in tags:
                tags.append(item)
            if len(tags) >= max_tags:
                break

        return tags

    def tag_image(
        self,
        image_path: str,
        custom_prompt: Optional[str] = None,
        max_tags: int = 8,
        status_callback: Optional[Callable[[str], None]] = None
    ) -> List[str]:
        """
        Runs SmolVLM inference on the provided image and returns extracted tags.
        """
        if not self.is_loaded:
            success = self.load_model(status_callback)
            if not success:
                return []

        try:
            import torch

            p = Path(image_path)
            if not p.exists():
                return []

            with Image.open(p) as img:
                # Convert to RGB and scale to efficient resolution
                rgb_img = img.convert("RGB")
                # Using 384x384 maximizes inference speed on CPU while preserving detail
                rgb_img.thumbnail((384, 384))

                default_instruction = "List the main items, objects, and subjects in this photo as a comma-separated list of short tags:"
                user_text = custom_prompt.strip() if custom_prompt and custom_prompt.strip() else default_instruction

                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image"},
                            {"type": "text", "text": user_text}
                        ]
                    }
                ]

                inputs = self.processor.apply_chat_template(messages, add_generation_prompt=True)
                model_inputs = self.processor(text=inputs, images=[rgb_img], return_tensors="pt")
                model_inputs = {k: v.to(self.device) for k, v in model_inputs.items()}

                with torch.no_grad():
                    generated_ids = self.model.generate(
                        **model_inputs,
                        max_new_tokens=30,
                        do_sample=False,
                        num_beams=1
                    )

                prompt_len = model_inputs["input_ids"].shape[1]
                generated_tokens = generated_ids[:, prompt_len:]
                output_text = self.processor.batch_decode(
                    generated_tokens,
                    skip_special_tokens=True
                )[0].strip()

                tags = self.extract_tags_from_text(output_text, max_tags=max_tags)
                return tags
        except Exception as e:
            if status_callback:
                status_callback(f"Error during tagging: {e}")
            return []
