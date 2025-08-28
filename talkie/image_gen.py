import base64
import logging
import tempfile
import threading
from pathlib import Path
from typing import Final, Literal

from openai import OpenAI
from PIL import Image

from .cache import FileCache

ImageSize = Literal[
    "auto",
    "1024x1024",
    "1536x1024",
    "1024x1536",
    "256x256",
    "512x512",
    "1792x1024",
    "1024x1792",
]

ImageModel = Literal["dall-e-3", "gpt-image-1"]

Quality = Literal["standard", "hd", "low", "medium", "high", "auto"]


class ImageGen:
    def __init__(self, open_ai: OpenAI, cache: FileCache):
        print(cache.cache_dir)
        self.model: ImageModel = "gpt-image-1"
        self.size: ImageSize = "1024x1024"
        self.quality: Quality = "medium"

        self.client: Final = open_ai
        self.cache: Final = cache
        cache.meta = {
            "model": self.model,
            "size": self.size,
            "quality": self.quality,
        }
        self.stop_event: Final = threading.Event()

    def _make_image_file(self, data: bytes) -> Path:
        target = Path("temp.png")
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_bytes(data)
        return target

    def generate_image(self, description: str, key: str | None = None) -> Path:
        if key is None:
            key = description
        cached_data = self.cache.get(key)
        if cached_data:
            return self._make_image_file(cached_data)

        logging.info("Generating image")
        try:
            response = self.client.images.generate(
                model=self.model,
                prompt=description,
                size=self.size,
                quality=self.quality,
                # style="natural",
                n=1,
            )
            logging.info("Generating done")

            if not response.data:  # or not response.data[0].url:
                raise RuntimeError("No image URL returned from OpenAI API")

            base_64 = response.data[0].b64_json
            data: bytes | None = None
            if base_64:
                data = base64.b64decode(base_64)
            else:
                image_url = response.data[0].url
                if image_url:
                    import requests

                    img_response = requests.get(image_url)
                    img_response.raise_for_status()
                    data = img_response.content

            if data is None:
                raise RuntimeError("No image data found")

            self.cache.add(key, data)
            return self._make_image_file(data)

        except Exception as e:
            raise RuntimeError("Failed to generate image") from e

    def generate_image_with_base(
        self, description: str, base_image_path: Path | str, key: str | None = None
    ) -> Path:
        if key is None:
            key = f"{description}_{Path(base_image_path).name}"

        cached_data = self.cache.get(key)
        if cached_data:
            return self._make_image_file(cached_data)

        logging.info("Generating image with base image")
        try:
            base_path = Path(base_image_path)
            if not base_path.exists():
                raise FileNotFoundError(f"Base image not found: {base_path}")

            # Convert image to RGBA format required by OpenAI
            with Image.open(base_path) as img:
                if img.mode != "RGBA":
                    img = img.convert("RGBA")

                # Save to temporary file
                with tempfile.NamedTemporaryFile(
                    suffix=".png", delete=False
                ) as temp_file:
                    img.save(temp_file, format="PNG")
                    temp_path = Path(temp_file.name)

            try:
                print("### " + description)
                with open(temp_path, "rb") as rgba_file:
                    response = self.client.images.edit(
                        image=rgba_file,
                        model="gpt-image-1",
                        prompt=description,
                        size="1024x1024",
                        n=1,
                    )
            finally:
                # Clean up temporary file
                temp_path.unlink(missing_ok=True)
            logging.info("Generation with base image done")

            if not response.data:
                raise RuntimeError("No image URL returned from OpenAI API")

            base_64 = response.data[0].b64_json
            data: bytes | None = None
            if base_64:
                data = base64.b64decode(base_64)
            else:
                image_url = response.data[0].url
                if image_url:
                    import requests

                    img_response = requests.get(image_url)
                    img_response.raise_for_status()
                    data = img_response.content

            if data is None:
                raise RuntimeError("No image data found")

            self.cache.add(key, data)
            return self._make_image_file(data)

        except Exception as e:
            raise RuntimeError("Failed to generate image with base") from e

    def get_image(self, key: str) -> None | Path:
        cached_data = self.cache.get(key)
        if cached_data:
            return self._make_image_file(cached_data)
        return None
