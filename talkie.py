import base64
from concurrent.futures import Future
import logging
from pathlib import Path
from typing import Literal
import openai
from openai.types.responses import response_status
import pixpy as pix
import subprocess
import threading
import queue
import re

from cache import FileCache
from utils.wrap import wrap_lines
from tts_handler import TextToSpeech
from voice_recorder import VoiceToText

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


def parse_text(text: str, patterns: dict[str, str]) -> dict[str, str]:
    """Parse a description by matching named regex patterns and removing matches from text.

    Args:
        text: The input text to parse
        patterns: Dict mapping names to regex patterns

    Returns:
        Dict with 'text' key containing remaining text and other keys for named matches
    """
    result = {}
    remaining_text = text

    for name, pattern in patterns.items():
        match = re.search(pattern, remaining_text, re.MULTILINE)
        if match:
            result[name] = match.group(0)
            # Remove the match and any trailing newline to avoid double newlines
            match_text = match.group(0)
            if remaining_text[match.start() : match.end() + 1].endswith("\n"):
                match_text += "\n"
            remaining_text = remaining_text.replace(match_text, "", 1).strip()
        else:
            result[name] = ""

    result["text"] = remaining_text
    return result


def parse_adventure_description(text: str) -> dict[str, str]:
    return parse_text(
        text,
        {
            "title": r"^(.*)\s{5,}(.*)$",
            "header": r"^Using normal.*\nLoading.*$",
            "trademark": r"^.*trademark.*nfocom.*$",
            "release": r"^Release.*Serial.*$",
            "prompt": r"\n+>",
            "copyright": r"^Copyright (.*)",
        },
    )

def unwrap_text(text: str, colum: int = 200) -> str:
    """
    Try to unwrap wrapped text. Assumes any line that is longer than 'column' and does not end in punctuation should be joined with the next line.
    """

    pattern = re.compile(r"[.?!>:]$")
    new_lines : list[str] = []
    last_line: str  = ""
    for line in text.splitlines():
        if len(line) > colum and not pattern.search(line):
            if last_line != "":
                last_line = last_line + " " + line
            else:
                last_line = line
        else:
            if last_line != "":
                new_lines.append(last_line + " " + line) 
                last_line = ""
            else:
                new_lines.append(line)
    if last_line != "":
        new_lines.append(last_line) 

    return "\n".join(new_lines)

def trim_lines(text: str) -> str:
    """Trim spaces from the beginning and end of all lines in 'text'"""
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(lines)

class IFPlayer:
    def __init__(self, file_name: Path):
        zcode = re.compile(r"\.z(ode|[123456789])$")
        self.proc = subprocess.Popen(
            ["dfrotz", "-m", "-w", "1000", file_name.as_posix()],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.output_queue: queue.Queue[bytes] = queue.Queue()

        def read_output():
            if self.proc.stdout:
                while True:
                    data : bytes = self.proc.stdout.read1(16384)  # type: ignore
                    if not data:
                        break
                    logging.info(f"OUT: '{data.decode()}'")
                    self.output_queue.put(data)

        self.output_thread = threading.Thread(target=read_output, daemon=True)
        self.output_thread.start()

    def read(self) -> str | None:
        try:
            text = self.output_queue.get_nowait()
            return text.decode()
        except queue.Empty:
            pass
        return None

    def write(self, text: str):
        if self.proc.stdin is not None:
            logging.info(f"IN: '{text}'")
            _ = self.proc.stdin.write(text.encode())
            self.proc.stdin.flush()


whisper_prompt = """
The following recording is a single sentence command to control text adventure or interactive fiction story.
It is usually in the form <verb> <noun> or <verb> <noun> <preposition> <noun>.

Common commands
- Look, examine <object>
- go north / south / east / west
- drop sword, take scroll

This is the current situation to which the command probably relates:
```
{text}
```
"""


def main():

    logging.getLogger().setLevel(logging.INFO)
    screen = pix.open_display(size=(1280, 1024))
    tile_set = pix.TileSet(font_file="3270.ttf", size = 32)
    con_size = (screen.size / tile_set.tile_size).toi()
    console = pix.Console(tile_set=tile_set, cols=con_size.x, rows=con_size.y)

    tts = TextToSpeech(voice="alloy")
    voice = VoiceToText()
    desc = ""
    fields: dict[str, str] = {}

    # To deal with permission
    # voice.record_audio(0.1)

    player = IFPlayer(Path("lurkinghorror.z3"))
    current_image : None | pix.Image = None

    image_gen = ImageGen()
    image_prompt = ""

    console.read_line() 
    recording = False
    vtt_future: Future[str] | None = None
    pattern = re.compile(r"[.?!>:]$")
    while pix.run_loop():
        screen.draw(drawable=console, top_left=(0, 0), size=console.size)
        if pix.was_pressed(pix.key.ESCAPE):
            tts.stop_playing()
        if pix.is_pressed(pix.key.F5):
            screen.draw_color = pix.color.LIGHT_GREEN
            screen.filled_circle(center=(20, 20), radius=18)
            screen.draw_color = pix.color.WHITE
            if not recording:
                voice.start_transribe()
                recording = True
        elif recording:
            vtt_future = voice.end_transcribe(prompt=whisper_prompt.format(**fields))
            recording = False

        if vtt_future is not None and vtt_future.done():
            text = vtt_future.result()
            vtt_future = None
            text += "\n"
            console.cancel_line()
            console.write(text)
            player.write(text)
            console.read_line()

        text = player.read()
        if text:
            text = trim_lines(text)
            text = unwrap_text(text)
            fields = parse_adventure_description(text)
            desc = fields["text"]
            image_prompt = f"Following is a description of a scene from a interactive fiction (text adventure). Generate an image to go with it. Use a 80s retro semi realistic style. Don't include too many details. NOTE: *Dont* include distinct objects in the foreground that are not part of the description. *Dont* include text from the description in the image.\n```\n{desc}\n```"

            for paragraph in desc.split("\n\n"):
                if len(paragraph.strip()) > 0:
                    if not pattern.search(paragraph):
                        paragraph += ". "
                        paragraph = paragraph.replace("ZORK I", "ZORK ONE").replace("A N C H O R H E A D", "### ANCHORHEAD")
                    tts.speak(paragraph)
            if console.reading_line:
                console.cancel_line()
            console.write("\n")
            for line in wrap_lines(desc.splitlines(), console.grid_size.x - 1):
                console.write(line + "\n")
            console.write("\n>")
            console.read_line()
            image_file = image_gen.get_image(image_prompt)
            if image_file:
                current_image = pix.load_png(image_file)

        for e in pix.all_events():
            if isinstance(e, pix.event.Key):
                current_image = None
            if isinstance(e, pix.event.Text):
                console.set_color(pix.color.LIGHT_BLUE, pix.color.BLACK)
                console.write(e.text)
                console.set_color(pix.color.WHITE, pix.color.BLACK)
                if e.text[0] == "/":
                    cmd = e.text[1:].strip()
                    print(cmd)
                    if cmd == "image":
                        image = image_gen.generate_image(image_prompt)
                        current_image = pix.load_png(image)
                else:
                    player.write(e.text)
                console.read_line()

        if current_image:
            screen.draw_color = 0x00000080
            screen.filled_rect(top_left=(0,0), size=screen.size)
            screen.draw_color = pix.color.WHITE
            sz = current_image.size / 2
            xy = (screen.size - sz) / 2
            screen.draw(current_image, top_left=xy, size=sz)
        screen.swap()


if __name__ == "__main__":
    main()
