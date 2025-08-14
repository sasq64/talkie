import base64
import logging
from pathlib import Path
from typing import Literal
import openai
import threading

from cache import FileCache

ImageSize = Literal["auto", "1024x1024", "1536x1024", "1024x1536", "256x256", "512x512", "1792x1024", "1024x1792"]

ImageModel = Literal["dall-e-3", "gpt-image-1"]

class ImageGen:
    def __init__(self):
        self.client = None
        self.model : ImageModel = "gpt-image-1"
        self.size : ImageSize ="1024x1024"
        self.quality="medium"

        self.cache = FileCache(
            Path(".cache/img"), meta={
                "model": self.model,
                "size": self.size,
                "quality": self.quality,
            }
        )
        self.stop_event = threading.Event()

        # Load OpenAI API key
        key_path = Path.home() / ".openai.key"
        if key_path.exists():
            with open(key_path, "r") as f:
                api_key = f.read().strip()
            self.client = openai.OpenAI(api_key=api_key)

    def _make_image_file(self, data: bytes) -> Path:
        target = Path("temp.png")
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, 'wb') as f:
            f.write(data)
        return target
    
    def generate_image(self, description) -> Path:
        if not self.client:
            raise RuntimeError("OpenAI client not initialized. Check if ~/.openai.key exists.")
        
        cached_data = self.cache.get(description)
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
            
            if not response.data: # or not response.data[0].url:
                raise RuntimeError("No image URL returned from OpenAI API")
                
            base_64 = response.data[0].b64_json
            if base_64:
                data = base64.b64decode(base_64)
            else:
                image_url = response.data[0].url
                
                import requests
                img_response = requests.get(image_url)
                img_response.raise_for_status()
                data = img_response.content
            
            self.cache.add(description, data)
            return self._make_image_file(data)
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate image: {e}")

    def get_image(self, description: str) -> None | Path:
        cached_data = self.cache.get(description)
        if cached_data:
            return self._make_image_file(cached_data)
        return None