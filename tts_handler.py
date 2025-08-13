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
        self.current_stream = None
        self.stop_event = threading.Event()
        
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
                    self.current_stream = self.pyaudio_instance.open(
                        format=self.pyaudio_instance.get_format_from_width(audio_segment.sample_width),
                        channels=audio_segment.channels,
                        rate=audio_segment.frame_rate,
                        output=True
                    )
                    
                    # Play the audio in chunks, checking for stop event
                    chunk_size = 1024
                    for i in range(0, len(raw_data), chunk_size):
                        if self.stop_event.is_set():
                            break
                        chunk = raw_data[i:i+chunk_size]
                        self.current_stream.write(chunk)
                    
                    if self.current_stream:
                        self.current_stream.stop_stream()
                        self.current_stream.close()
                        self.current_stream = None
                    self.stop_event.clear()
            except Exception as e:
                print(f"Audio playback error: {e}")
                if self.current_stream:
                    self.current_stream.close()
                    self.current_stream = None
    
    def stop_playing(self):
        self.stop_event.set()
        
    def clear_all(self):
        # Clear the audio queue to stop any queued audio
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
    
    def cleanup(self):
        self.stop_playing()
        self.pyaudio_instance.terminate()