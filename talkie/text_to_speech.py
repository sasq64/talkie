from typing import Final, Literal
import openai
import logging
import pyaudio
import io
import threading
import queue
from queue import Queue
from pathlib import Path
from pydub import AudioSegment
from .cache import FileCache

Voice = Literal["alloy", "ash", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse"]


class TextToSpeech:
    def __init__(self, voice: Voice = "alloy", model: str = "tts-1"):
        self.tts_queue : Final = Queue[str]()
        self.audio_queue : Final = Queue[bytes]()
        self.pyaudio_instance : Final = pyaudio.PyAudio()
        self.voice : str = voice
        self.model : str = model
        self.cache : Final = FileCache(
            Path(".cache/tts"), meta={"voice": voice, "model": model}
        )

        self.stop_event : Final = threading.Event()

        # Load OpenAI API key
        api_key = ""
        key_path = Path.home() / ".openai.key"
        if key_path.exists():
            with open(key_path, "r") as f:
                api_key = f.read().strip()
        self.client : Final = openai.OpenAI(api_key=api_key)

        # Start worker threads
        self.tts_thread : Final = threading.Thread(target=self._tts_worker, daemon=True)
        self.audio_thread : Final = threading.Thread(target=self._audio_worker, daemon=True)
        self.tts_thread.start()
        self.audio_thread.start()

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
                        logging.info(f"TTS: '{text}' found in cache!")
                        self.audio_queue.put(fn)
                    else:
                        logging.info(f"TTS: Using '{self.voice}' to generate audio for '{text}'")
                        response = self.client.audio.speech.create(
                            model=self.model, voice=self.voice, input=text
                        )
                        audio_data = response.content
                        self.cache.add(text, audio_data)
                        self.audio_queue.put(audio_data)
            except Exception as e:
                logging.error(f"TTS Error: {e}")

    def _audio_worker(self):
        current_stream: pyaudio.Stream | None = None
        while True:
            try:
                audio_data = self.audio_queue.get()
                self.stop_event.clear()
                if audio_data:
                    # Path(f"file{counter}.mp3").write_bytes(audio_data)
                    # counter += 1

                    # Convert MP3 bytes to AudioSegment
                    audio_segment  : AudioSegment = AudioSegment.from_mp3(io.BytesIO(audio_data))

                    # Convert to raw audio data for pyaudio
                    raw_data : bytes = audio_segment.raw_data

                    # Set up pyaudio stream with correct format
                    current_stream = self.pyaudio_instance.open(
                        format=self.pyaudio_instance.get_format_from_width(
                            audio_segment.sample_width
                        ),
                        channels=audio_segment.channels,
                        rate=audio_segment.frame_rate,
                        output=True,
                    )

                    # Play the audio in chunks, checking for stop event
                    chunk_size = 1024
                    for i in range(0, len(raw_data), chunk_size):
                        if self.stop_event.is_set():
                            break
                        chunk = raw_data[i : i + chunk_size]
                        current_stream.write(chunk)

                    current_stream.stop_stream()
                    current_stream.close()
                    current_stream = None
                    self.stop_event.clear()
            except Exception as e:
                logging.error(f"Audio playback error: {e}")
                if current_stream:
                    current_stream.close()
                    current_stream = None

    def stop_playing(self):
        self.stop_event.set()

    def clear_all(self):
        # Clear the audio queue to stop any queued audio
        while not self.audio_queue.empty():
            try:
                _ = self.audio_queue.get_nowait()
            except queue.Empty:
                break

    def stop_all(self):
        self.clear_all()
        self.stop_playing()

    def cleanup(self):
        self.stop_playing()
        self.pyaudio_instance.terminate()
