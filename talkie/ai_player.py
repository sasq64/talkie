import logging
import re
from concurrent.futures import Future  # noqa: TC003
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .adventure_guy import AdventureGuy
from .if_player import IFPlayer
from .talkie_config import TalkieConfig
from pixtools import ImageGen, TextToSpeech
from pixtools.voice_recorder import VoiceToText


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
    def __init__(
        self,
        if_player: IFPlayer,
        config: TalkieConfig,
        text_to_speech: TextToSpeech | None = None,
        voice_to_text: VoiceToText | None = None,
        image_gen: ImageGen | None = None,
        adventure_guy: AdventureGuy | None = None,
    ):
        self.prompts: Final = config.prompts
        self.image_prompt: Final = self.prompts["image_prompt"]
        self.modernize_prompt: Final = self.prompts["modernize_prompt"]
        self.whisper_prompt: Final = self.prompts["whisper_prompt"]

        self.adventure_guy: AdventureGuy | None = adventure_guy
        self.smart_parse: bool = False

        self.prompt_fields: dict[str, str] = {}

        self.tts: Final = text_to_speech
        self.voice: Final = voice_to_text
        self.player: Final = if_player
        self.image_gen: Final = image_gen
        self.image_file: Path | None = None

        self.output: list[AIOutput] = []

        self.desc: str = ""
        self.recording: bool = False
        self.vtt_future: Future[str] | None = None

    def update(self):
        """Update AI and return command if available"""
        self._check_voice_result()
        # Do we have an AI processed voice command?
        if self.adventure_guy and self.adventure_guy.update():
            command = self.adventure_guy.get_command()
            if command:
                self.output.append(PromptOutput(command))
                self.write_command(command)

        result = self.player.read()
        if result:
            self.desc = result.text
            self.prompt_fields["text"] = result.text
            first_image_file = None
            self.output.append(TextOutput(self.desc))

            if result.image:
                self.image_file = result.image
                self.output.append(ImageOutput(self.image_file))

            # Process TTS for paragraphs
            for paragraph in self.desc.split("\n\n"):
                paragraph = paragraph.strip()
                if len(paragraph) > 0:
                    if self.image_gen:
                        image_file = self.image_gen.get_image(paragraph)
                        logging.info(f"'{paragraph}' gave image {image_file}")
                        if image_file and not first_image_file:
                            first_image_file = image_file
                            self.output.append(ImageOutput(image_file))

                    if self.tts:
                        pattern = re.compile(r"[.?!>:]$")
                        if not pattern.search(paragraph):
                            paragraph += ". "
                        self.tts.speak(paragraph)

    def get_next_output(self) -> AIOutput | None:
        # image_file = self.player.get_image()
        # if image_file:
        #    return ImageOutput(image_file)
        if len(self.output) == 0:
            return None
        return self.output.pop(0)

    def start_voice_recording(self):
        """Start voice recording"""
        if not self.voice:
            return
        if not self.recording:
            self.voice.start_transribe()
            self.recording = True

    def end_voice_recording(self):
        """End voice recording and return future"""
        if not self.voice:
            return
        if self.recording:
            self.vtt_future = self.voice.end_transcribe(
                prompt=self.whisper_prompt.format(**self.prompt_fields)
            )
            self.recording = False

    def _check_voice_result(self):
        """Check if voice transcription is ready and process it"""
        if self.vtt_future is not None and self.vtt_future.done():
            text = self.vtt_future.result()
            self.vtt_future = None
            if self.smart_parse and self.adventure_guy:
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
            if para and self.image_gen:
                logging.info(f"Generate image with key '{para}'")
                self.image_file = self.image_gen.generate_image(
                    self.image_prompt.format(**self.prompt_fields), para
                )
                self.output.append(ImageOutput(self.image_file))
        elif cmd == "mod" and self.image_gen:
            if self.image_file:
                prompt = self.modernize_prompt.format(**self.prompt_fields)
                file_name = self.image_gen.generate_image_with_base(
                    prompt, self.image_file, para
                )
                self.output.append(ImageOutput(file_name))
        elif cmd == "transcript":
            print(self.player.get_transcript())
        else:
            return False
        return True

    def key_mode(self) -> bool:
        return self.player.key_mode

    def write_command(self, text: str):
        """Write command to game"""
        self.image_file = None
        self.player.write(text)

    def stop_audio(self):
        """Stop all audio"""
        if self.tts:
            self.tts.stop_all()

    def stop_playing(self):
        """Stop TTS playing"""
        if self.tts:
            self.tts.stop_playing()

    def close(self):
        """Close the AI player and cleanup resources."""
        # Stop any ongoing operations
        self.stop_audio()
        self.stop_playing()

        # Close the IF player subprocess
        if hasattr(self, "player"):
            self.player.close()
