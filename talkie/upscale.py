import time
from pathlib import Path

import pixpy as pix
import requests


class Upscaler:
    def __init__(self, api_key: str | None = None):
        self.upscale_id: str | None = None
        self.upscale_time: float = 0.0
        self.api_key = ""
        if api_key is not None:
            self.api_key = api_key
        else:
            key_file = Path(Path.home() / ".stability.key")
            if key_file.exists():
                self.api_key = key_file.read_text().strip()

    def upscale(self, image: Path):
        with open(image, "rb") as f:
            response = requests.post(
                "https://api.stability.ai/v2beta/stable-image/upscale/creative",
                headers={
                    "authorization": f"Bearer {self.api_key}",
                    "accept": "image/*",
                },
                files={"image": f},
                data={
                    "prompt": "Amiga 16 color lowres image from the text adventure game The Pawn",
                    "output_format": "png",
                },
            )
        self.upscale_id = response.json().get("id")
        print(f"Generation ID:{self.upscale_id}")
        self.upscale_time = time.time() + 12

    def fast_upscale(self, image: Path) -> pix.Image | None:
        with open(image, "rb") as f:
            response = requests.post(
                "https://api.stability.ai/v2beta/stable-image/upscale/fast",
                headers={
                    "authorization": f"Bearer {self.api_key}",
                    "accept": "image/*",
                },
                files={
                    "image": f,
                },
                data={
                    "output_format": "png",
                },
            )

        if response.status_code == 200:
            with open("./scaled.png", "wb") as file:
                file.write(response.content)
            return pix.load_png("scaled.png")
        else:
            raise Exception(str(response.json()))

    def check_upscale(self) -> bool:
        if self.upscale_id and self.upscale_time > time.time():
            self.upscale_time += 10.2
            response = requests.request(
                "GET",
                f"https://api.stability.ai/v2beta/results/{self.upscale_id}",
                headers={
                    "accept": "image/*",  # Use 'application/json' to receive base64 encoded JSON
                    "authorization": f"Bearer {self.api_key}",
                },
            )
            if response.status_code == 202:
                print("Generation in-progress, try again in 10 seconds.")
                return False
            elif response.status_code == 200:
                self.upscale_id = None
                print("Generation complete!")
                with open("result.png", "wb") as file:
                    file.write(response.content)
                return True
            else:
                self.upscale_id = None
                raise Exception(str(response.json()))
        return False
