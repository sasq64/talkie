import threading
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
        cache: FileCache,
        open_ai: openai.OpenAI,
        voice: Voice | None = None,
        model: str = "tts-1",
    ):
        print(f"{cache.cache_dir}")
        self.tts_queue: Final = Queue[str]()
        self.audio_player: Final = audio_player
        self.voice: str = voice
        self.cache: Final = cache
        self.cache.set_meta({"voice": voice, "model": model})
        self.model: str = model
        self.client: Final = open_ai

        # Start worker thread
        self.tts_thread: Final = threading.Thread(target=self._tts_worker, daemon=True)
        self.tts_thread.start()

    def speak(self, text: str):
        """Queue text for speaking."""
        text = text.strip()
        if self.client and text:
            self.tts_queue.put(text)

    def _tts_worker(self):
        while True:
            try:
                text = self.tts_queue.get()
                if text:
                    fn = self.cache.get(text)
                    if fn is not None:
                        logger.info(f"'{text}' found in cache!")
                        self.audio_player.put_audio(fn)
                    else:
                        logger.info(
                            f"Using '{self.voice}' to generate audio for '{text}'"
                        )
                        response = self.client.audio.speech.create(
                            model=self.model, voice=self.voice, input=text
                        )
                        audio_data = response.content
                        self.cache.add(text, audio_data)
                        self.audio_player.put_audio(audio_data)
            except Exception as e:
                logger.error(f"Error: {e}")

    def stop_playing(self):
        self.audio_player.stop_playing()

    def clear_all(self):
        self.audio_player.clear_all()

    def stop_all(self):
        self.audio_player.stop_all()

    def cleanup(self):
        self.audio_player.cleanup()
