import time
import unittest
from unittest.mock import MagicMock, Mock, patch
import tempfile
import shutil
from pathlib import Path

from talkie.text_to_speech import TextToSpeech


class TestTextToSpeech(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures with mocked dependencies."""
        # Create temporary directory for cache
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock AudioPlayer
        self.mock_audio_player = Mock()
        
        # Mock OpenAI client and response
        self.mock_openai_client = Mock()
        self.mock_response = Mock()
        self.mock_response.content = b"fake_audio_data"
        self.mock_openai_client.audio.speech.create.return_value = self.mock_response

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_speak_calls_openai_and_sends_to_audio_player(self):
        """Test that speak() calls OpenAI API and sends audio data to AudioPlayer."""
        # Set up cache mock to return None (cache miss - caches nothing)
        mock_cache = Mock()
        mock_cache.get.return_value = None
        
        # Create TextToSpeech instance
        tts = TextToSpeech(
            audio_player=self.mock_audio_player,
            cache=mock_cache,
            open_ai=self.mock_openai_client,
            voice="alloy",
            model="tts-1"
        )
        
        # Call speak with test text
        test_text = "Hello, world!"
        tts.speak(test_text)
        
        # Give the worker thread time to process
        time.sleep(0.1)
        
        # Verify OpenAI API was called with correct parameters
        self.mock_openai_client.audio.speech.create.assert_called_once_with(
            model="tts-1",
            voice="alloy", 
            input=test_text
        )
        
        # Verify audio data was cached
        mock_cache.add.assert_called_once_with(test_text, b"fake_audio_data")
        
        # Verify audio data was sent to AudioPlayer
        self.mock_audio_player.put_audio.assert_called_once_with(b"fake_audio_data")


if __name__ == "__main__":
    unittest.main()