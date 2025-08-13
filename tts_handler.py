import openai
import pyaudio
import io
import threading
import queue
from pathlib import Path
from pydub import AudioSegment
from cache import FileCache


class TTSHandler:
    def __init__(self):
        self.client = None
        self.tts_queue = queue.Queue()
        self.audio_queue = queue.Queue()
        self.pyaudio_instance = pyaudio.PyAudio()
        self.cache = FileCache(Path(".cache/tts"))
        
        # Load OpenAI API key
        key_path = Path.home() / '.openai.key'
        if key_path.exists():
            with open(key_path, 'r') as f:
                api_key = f.read().strip()
            self.client = openai.OpenAI(api_key=api_key)
        
        # Start worker threads
        self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self.audio_thread = threading.Thread(target=self._audio_worker, daemon=True)
        self.tts_thread.start()
        self.audio_thread.start()
    
    def speak(self, text):
        text = text.strip()
        if self.client and text:
            fn = self.cache.get(text)
            if fn is not None:
                print("### CACHED!")
                self.audio_queue.put(fn)
            else:
                self.tts_queue.put(text)
    
    def _tts_worker(self):
        while True:
            try:
                text = self.tts_queue.get()
                if text:
                    print(f"TTS {text}")
                    response = self.client.audio.speech.create(
                        model="tts-1",
                        voice="alloy",
                        input=text
                    )
                    audio_data = response.content
                    self.cache.add(text, audio_data)
                    self.audio_queue.put(audio_data)
            except Exception as e:
                print(f"TTS Error: {e}")
    
    def _audio_worker(self):
        while True:
            try:
                audio_data = self.audio_queue.get()
                if audio_data:
                    print("Convert MP3")
                    # Convert MP3 bytes to AudioSegment
                    audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))
                    
                    # Convert to raw audio data for pyaudio
                    raw_data = audio_segment.raw_data
                    print("STREAM")
                    
                    # Set up pyaudio stream with correct format
                    stream = self.pyaudio_instance.open(
                        format=self.pyaudio_instance.get_format_from_width(audio_segment.sample_width),
                        channels=audio_segment.channels,
                        rate=audio_segment.frame_rate,
                        output=True
                    )
                    
                    # Play the audio
                    stream.write(raw_data)
                    stream.stop_stream()
                    stream.close()
            except Exception as e:
                print(f"Audio playback error: {e}")
    
    def cleanup(self):
        self.pyaudio_instance.terminate()