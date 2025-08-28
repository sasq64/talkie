import queue
import subprocess
import tempfile
import threading
from logging import getLogger
from queue import Queue
from typing import Final

import pyaudio

logger = getLogger(__name__)


class AudioPlayer:
    def __init__(self):
        self.audio_queue: Final = Queue[bytes]()
        self.pyaudio_instance: Final = pyaudio.PyAudio()
        self.stop_event: Final = threading.Event()

        # Start audio worker thread
        self.audio_thread: Final = threading.Thread(
            target=self._audio_worker, daemon=True
        )
        self.audio_thread.start()

    def put_audio(self, audio_data: bytes):
        """Add audio data to the playback queue."""
        if audio_data:
            self.audio_queue.put(audio_data)

    def _audio_worker(self):
        current_stream: pyaudio.Stream | None = None
        while True:
            try:
                audio_data = self.audio_queue.get()
                self.stop_event.clear()
                if audio_data:
                    # Use ffmpeg to decode MP3 to raw PCM
                    with tempfile.NamedTemporaryFile(
                        suffix=".mp3", delete=False
                    ) as temp_mp3:
                        _ = temp_mp3.write(audio_data)
                        temp_mp3.flush()

                        # Convert MP3 to raw PCM using ffmpeg
                        result = subprocess.run(
                            [
                                "ffmpeg",
                                "-i",
                                temp_mp3.name,
                                "-f",
                                "s16le",  # 16-bit little endian PCM
                                "-ar",
                                "22050",  # 22050 Hz sample rate
                                "-ac",
                                "1",  # mono
                                "-",
                            ],
                            capture_output=True,
                            check=True,
                        )

                        raw_data = result.stdout

                    # Set up pyaudio stream with correct format
                    format = self.pyaudio_instance.get_format_from_width(2, False)
                    current_stream = self.pyaudio_instance.open(
                        format=format,
                        channels=1,
                        rate=22050,
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
                logger.error(f"Audio playback error: {e}")
                if current_stream:
                    current_stream.close()
                    current_stream = None

    def stop_playing(self):
        """Stop the currently playing audio."""
        self.stop_event.set()

    def clear_all(self):
        """Clear the audio queue to stop any queued audio."""
        while not self.audio_queue.empty():
            try:
                _ = self.audio_queue.get_nowait()
            except queue.Empty:
                break

    def stop_all(self):
        """Stop all audio playback and clear the queue."""
        self.clear_all()
        self.stop_playing()

    def cleanup(self):
        """Clean up resources."""
        self.stop_playing()
        self.pyaudio_instance.terminate()
