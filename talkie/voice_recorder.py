import time
import wave
from collections.abc import Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from logging import getLogger
from pathlib import Path
from typing import Final

import pyaudio
from openai import NOT_GIVEN, OpenAI

logger = getLogger(__name__)


def fixup(text: str) -> str:
    return text.lower().replace(" ", "_")[:40]


class VoiceToText:
    def __init__(self, client: OpenAI):
        """Initialize VoiceToText with optional API key"""
        self.client = client
        self._current_recording: list[bytes] | None = None
        self._sample_rate: float = 32000
        self._executor: Final = ThreadPoolExecutor(max_workers=2)
        self._pyaudio: Final = pyaudio.PyAudio()
        self._stream: pyaudio.Stream | None = None
        self._is_recording: bool = False

    def start_recording(self, sample_rate: float | None = None) -> None:
        """Start recording audio"""
        if sample_rate is not None:
            self._sample_rate = sample_rate
        self._current_recording = []
        self._is_recording = True

        # _StreamCallback: TypeAlias = Callable[[bytes | None, int, Mapping[str, float], int], tuple[bytes | None, int]]
        def callback(
            in_data: bytes | None,
            _frame_count: int,
            _time_info: Mapping[str, float],
            _status: int,
        ) -> tuple[bytes | None, int]:
            # print(f"CALLBACK {self._is_recording} {self._current_recording} {len(in_data)}")
            if self._is_recording and self._current_recording is not None and in_data:
                self._current_recording.append(in_data)
            return (in_data, pyaudio.paContinue)

        print("STARTING STREAM")
        self._stream = self._pyaudio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=int(self._sample_rate),
            input=True,
            stream_callback=callback,
            frames_per_buffer=1024,
        )

        self._stream.start_stream()

    def stop_recording(self) -> bytes:
        """Stop recording and return the audio data"""
        if self._current_recording is None or not self._is_recording:
            raise RuntimeError("No recording in progress")

        self._is_recording = False

        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

        audio_data = b"".join(self._current_recording)

        self._current_recording = None
        return audio_data

    def record_audio(self, duration: float = 5, sample_rate: float = 16000) -> bytes:
        """Record audio for specified duration"""

        frames: list[bytes] = []

        stream = self._pyaudio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=int(sample_rate),
            input=True,
            frames_per_buffer=1024,
        )

        for _ in range(0, int(sample_rate / 1024 * duration)):
            data = stream.read(1024)
            frames.append(data)

        stream.stop_stream()
        stream.close()

        # Convert to numpy array
        audio_data = b"".join(frames)
        return audio_data

    def transcribe_audio(self, audio_file_path: str, prompt: str | None) -> str:
        """Send audio to OpenAI for transcription"""
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    language="en",
                    temperature=0,
                    response_format="json",
                    prompt=NOT_GIVEN if prompt is None else prompt,
                    model="gpt-4o-transcribe",
                    file=audio_file,
                )
            logger.info(f"Transcribe result {transcript}")
            return transcript.text
        except Exception as e:
            raise Exception("Error during transcription") from e

    def start_transribe(self):
        logger.info("Start transcribe")
        self.start_recording()

    def end_transcribe(self, prompt: str | None = None) -> Future[str]:
        audio_data = self.stop_recording()
        logger.info(f"Ended transcribe with {len(audio_data)} bytes")
        if len(audio_data) < 12000:
            return self._executor.submit(lambda: "\n")

        # Save to temporary file
        # with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        #    temp_path = temp_file.name
        #    sf.write(file=temp_path, data=audio_data, samplerate=sample_rate)

        # Save to temporary WAV file
        temp_path = "out.wav"
        self._save_wav(temp_path, audio_data, self._sample_rate)

        # Transcribe on worker thread
        logger.debug(f"Transcribing... {temp_path}\n{prompt}")
        future = self._executor.submit(self._transcribe_and_cleanup, temp_path, prompt)
        return future

    def _save_wav(self, filename: str, audio_data: bytes, sample_rate: float) -> None:
        """Save audio data to WAV file"""

        with wave.open(filename, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 2 bytes for int16
            wav_file.setframerate(int(sample_rate))
            wav_file.writeframes(audio_data)

    def _transcribe_and_cleanup(self, temp_path: str, prompt: str | None) -> str:
        """Transcribe audio and clean up temporary file"""
        try:
            transcript = self.transcribe_audio(temp_path, prompt)
            _ = Path("out.wav").rename(fixup(transcript) + ".wav")
            return transcript
        finally:
            pass
            # Clean up temporary file
            # if os.path.exists(temp_path):
            #    os.unlink(temp_path)

    def __del__(self):
        """Cleanup PyAudio resources"""
        if hasattr(self, "_stream") and self._stream:
            self._stream.close()
        if hasattr(self, "_pyaudio"):
            self._pyaudio.terminate()


def main():
    # Load OpenAI API key
    api_key = ""
    key_path = Path.home() / ".openai.key"
    if key_path.exists():
        with open(key_path) as f:
            api_key = f.read().strip()
    client = OpenAI(api_key=api_key)
    vtt = VoiceToText(client)
    vtt.start_transribe()
    time.sleep(5)  # Record for 5 seconds
    future = vtt.end_transcribe()
    transcript = future.result()  # Wait for future and get result
    print(f"\nTranscription: {transcript}")


if __name__ == "__main__":
    main()
