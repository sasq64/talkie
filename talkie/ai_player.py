import logging
import re
from concurrent.futures import Future  # noqa: TC003
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .adventure_guy import AdventureGuy
from .if_player import IFPlayer
from .image_gen import ImageGen
from .text_to_speech import TextToSpeech
from .voice_recorder import VoiceToText
from .draw import PixelCanvas


@dataclass
class TextOutput:
    text: str


@dataclass
class AudioOuptut:
    audio: bytes


@dataclass
class ImageOutput:
    file_name: Path

@dataclass
class PromptOutput:
    text: str


AIOutput = TextOutput | AudioOuptut | ImageOutput | PromptOutput


class AIPlayer:
    def __init__(self, prompts: dict[str, str], game_path: Path):
        self.prompts: Final = prompts
        self.image_prompt: Final = prompts["image_prompt"]
        self.modernize_prompt: Final = prompts["modernize_prompt"]
        self.whisper_prompt: Final = prompts["whisper_prompt"]

        # AI components
        self.adventure_guy: Final = AdventureGuy(prompts["talk_prompt"])
        self.smart_parse: bool = False
        self.tts: Final = TextToSpeech(voice="alloy")
        self.voice: Final = VoiceToText()
        self.player: Final = IFPlayer(game_path)
        self.image_gen: Final = ImageGen()
        self.image_file : Path | None = None

        self.output: list[AIOutput] = []

        # Graphics components
        width,height = 160,96
        self.pcanvas: Final = PixelCanvas(width, height)
        self.colors: list[int] = [
            0, 0xff0000, 0x30e830, 0xffff00, 0x0000ff, 0xA06800, 0x00ffff, 0xffffff
        ]
        self.palette: list[int] = [0] * 64

        # State
        self.desc: str = ""
        self.fields: dict[str, str | Path] = {}
        self.recording: bool = False
        self.vtt_future: Future[str] | None = None
        self.pattern: Final = re.compile(r"[.?!>:]$")

    def update(self):
        """Update AI and return command if available"""
        self._check_voice_result()

        # Do we have an AI processed voice command?
        if self.adventure_guy.update():
            command = self.adventure_guy.get_command()
            if command:
                self.output.append(PromptOutput(command))
                self.write_command(command)

        result = self.player.read()
        if result:
            self.fields = result
            self.desc = str(self.fields["text"])
            first_image_file = None
            self.output.append(TextOutput(self.desc))

            if "image" in result:
                img_file = Path(result["image"])
                self.output.append(ImageOutput(img_file))
                self.image_file = img_file

            # Process TTS for paragraphs
            for paragraph in self.desc.split("\n\n"):
                paragraph = paragraph.strip()
                if len(paragraph) > 0:
                    image_file = self.image_gen.get_image(paragraph)
                    logging.info(f"'{paragraph}' gave image {image_file}")
                    if image_file and not first_image_file:
                        first_image_file = image_file
                        self.output.append(ImageOutput(image_file))

                    if not self.pattern.search(paragraph):
                        paragraph += ". "
                        paragraph = paragraph.replace("ZORK I", "ZORK ONE").replace(
                            "A N C H O R H E A D", "### ANCHORHEAD"
                        )
                    self.tts.speak(paragraph)

    def get_next_output(self) -> AIOutput | None:

        #image_file = self.player.get_image()
        #if image_file:
        #    return ImageOutput(image_file)
        if len(self.output) == 0:
            return None
        return self.output.pop(0)

    def start_voice_recording(self):
        """Start voice recording"""
        if not self.recording:
            self.voice.start_transribe()
            self.recording = True

    def end_voice_recording(self):
        """End voice recording and return future"""
        if self.recording:
            self.vtt_future = self.voice.end_transcribe(
                prompt=self.whisper_prompt.format(**self.fields)
            )
            self.recording = False

    def _check_voice_result(self):
        """Check if voice transcription is ready and process it"""
        if self.vtt_future is not None and self.vtt_future.done():
            text = self.vtt_future.result()
            self.vtt_future = None
            if self.smart_parse:
                self.adventure_guy.set_input(text, self.desc)
            else:
                self.output.append(PromptOutput(text))
                self.write_command(text + "\n")

    def handle_slash_command(self, cmd: str) -> bool:
        """Handle slash commands and return image path if applicable"""
        para: str | None = None
        paragraphs = self.desc.split("\n\n")
        while len(paragraphs) > 0 and len(paragraphs[0]) < 60:
            logging.debug("Removing short paragraph from image description")
            _ = paragraphs.pop(0)
        if len(paragraphs) > 0:
            para = paragraphs[0]
        if cmd == "image":
            if para:
                logging.info(f"Generate image with key '{para}'")
                self.image_file = self.image_gen.generate_image(
                    self.image_prompt.format(**self.fields), para
                )
                self.output.append(ImageOutput(self.image_file))
        elif cmd == "mod":
            prompt = self.modernize_prompt.format(**self.fields)
            file_name = self.image_gen.generate_image_with_base(prompt, self.image_file, para)
            self.output.append(ImageOutput(file_name))
        elif cmd == "transcript":
            print(self.player.get_transcript())
        else:
            return False
        return True

    def write_command(self, text: str):
        """Write command to game"""
        self.image_file = None
        self.player.write(text)

    def stop_audio(self):
        """Stop all audio"""
        self.tts.stop_all()

    def stop_playing(self):
        """Stop TTS playing"""
        self.tts.stop_playing()

    def close(self):
        """Close the AI player and cleanup resources."""
        # Stop any ongoing operations
        self.stop_audio()
        self.stop_playing()

        # Close the IF player subprocess
        if hasattr(self, 'player'):
            self.player.close()

