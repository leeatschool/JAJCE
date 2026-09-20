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
                    status_callback("Loading PyTorch & Vision-Language Model...")

                import torch
                # Optimize CPU thread allocation for fast inference
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
        """
        Cleans and standardizes generated text into a list of concise tags.
        Handles both comma-separated lists and descriptive natural language responses.
        """
        if not text:
            return []

        # If model returned direct comma-separated tags
        if "," in text and not re.search(r"\b(the image|in this|we can see|displays a|features a)\b", text, re.IGNORECASE):
            raw = [t.strip().lower() for t in text.split(",") if t.strip()]
            valid = []
            for t in raw:
                cleaned_t = re.sub(r"[^a-zA-Z0-9\s\-]", "", t).strip()
                if cleaned_t and len(cleaned_t) >= 2 and cleaned_t not in valid:
                    valid.append(cleaned_t)
            if valid:
                return valid[:max_tags]

        # For descriptive sentences, clean preamble boilerplate
        cleaned = re.sub(
            r"(?i)\b(the image displays a piece of|the image features a|the image contains a|"
            r"in the center of the image is a|which appears to be|which is a|which makes the|"
            r"symbol of|appears to be|there is a|there are|the primary focus is on the|"
            r"in the background|in the foreground)\b",
            "",
            text
        )

        chunks = re.split(r"[\.,;\n]", cleaned)
        tags = []
        stop_words = {
            "the", "a", "an", "and", "or", "in", "on", "at", "of", "with", "to",
            "is", "are", "was", "this", "that", "these", "those", "image", "picture",
            "photo", "simple", "piece", "combination", "style", "stand", "out", "prominently"
        }

        for c in chunks:
            c = re.sub(r"[^a-zA-Z0-9\s\-]", " ", c).strip().lower()
            words = [w for w in c.split() if w and w not in stop_words]
            if words:
                # Capture concise noun phrase (up to 3 words)
                phrase = " ".join(words[:3])
                if len(phrase) >= 2 and phrase not in tags:
                    tags.append(phrase)
                # Also include notable single nouns if long enough
                for w in words[:2]:
                    if len(w) >= 4 and w not in tags and w not in phrase:
                        tags.append(w)

        # Fallback if no tags could be extracted
        if not tags and text.strip():
            words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", text) if w.lower() not in stop_words]
            tags = list(dict.fromkeys(words))

        return tags[:max_tags]

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
                if status_callback:
                    status_callback(f"Image not found: {image_path}")
                return []

            if status_callback:
                status_callback(f"Preparing image: {p.name}...")

            with Image.open(p) as img:
                # Convert to RGB and scale to 384x384 for optimal CPU performance
                rgb_img = img.convert("RGB")
                rgb_img.thumbnail((384, 384))

                default_instruction = "Describe the main objects, subjects, text, and visual elements in this image:"
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

                if status_callback:
                    status_callback("Tokenizing inputs & image patches...")

                inputs = self.processor.apply_chat_template(messages, add_generation_prompt=True)
                model_inputs = self.processor(text=inputs, images=[rgb_img], return_tensors="pt")
                model_inputs = {k: v.to(self.device) for k, v in model_inputs.items()}

                if status_callback:
                    status_callback("Generating visual identifications with SmolVLM...")

                with torch.no_grad():
                    generated_ids = self.model.generate(
                        **model_inputs,
                        max_new_tokens=40,
                        do_sample=False,
                        num_beams=1
                    )

                prompt_len = model_inputs["input_ids"].shape[1]
                generated_tokens = generated_ids[:, prompt_len:]
                output_text = self.processor.batch_decode(
                    generated_tokens,
                    skip_special_tokens=True
                )[0].strip()

                if status_callback:
                    status_callback("Extracting and standardizing tags...")

                tags = self.extract_tags_from_text(output_text, max_tags=max_tags)

                if status_callback:
                    status_callback(f"Identified {len(tags)} tags: {', '.join(tags)}")

                return tags
        except Exception as e:
            if status_callback:
                status_callback(f"Error during tagging: {e}")
            return []
