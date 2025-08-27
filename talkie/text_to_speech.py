from concurrent.futures import Executor
from logging import getLogger
from queue import Queue
from typing import Final, Literal

import openai

from .audio_player import AudioPlayer
from .cache import FileCache

logger = getLogger(__name__)


Voice = Literal[
    "alloy", "ash", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse"
]


class TextToSpeech:
    def __init__(
        self,
        audio_player: AudioPlayer,
        executor: Executor,
        cache: FileCache,
        open_ai: openai.OpenAI,
        voice: Voice = "alloy",
        model: str = "tts-1",
    ):
        self.exception_queue: Final = Queue[Exception]()
        self.tts_queue: Final = Queue[str]()
        self.audio_player: Final = audio_player
        self.voice: str = voice
        self.cache: Final = cache
        self.cache.set_meta({"voice": voice, "model": model})
        self.model: str = model
        self.client: Final = open_ai
        self.executor = executor
        self.future = executor.submit(self._tts_worker)

    def speak(self, text: str):
        """Queue text for speaking."""
        text = text.strip()
        if self.client and text:
            self.tts_queue.put(text)
        if self.future.done():
            _ = self.future.result()

    def _tts_worker(self):
        while True:
            text = self.tts_queue.get()
            if text:
                fn = self.cache.get(text)
                if fn is not None:
                    logger.info(f"'{text}' found in cache!")
                    self.audio_player.put_audio(fn)
                else:
                    logger.info(f"Using '{self.voice}' to generate audio for '{text}'")
                    response = self.client.audio.speech.create(
                        model=self.model, voice=self.voice, input=text
                    )
                    audio_data = response.content
                    self.cache.add(text, audio_data)
                    self.audio_player.put_audio(audio_data)

    def stop_playing(self):
        self.audio_player.stop_playing()

    def clear_all(self):
        self.audio_player.clear_all()

    def stop_all(self):
        self.audio_player.stop_all()

    def cleanup(self):
        self.audio_player.cleanup()
