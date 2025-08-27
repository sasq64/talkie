import time
import tempfile
import shutil
from pathlib import Path
from typing import Iterable
from unittest.mock import Mock

from openai import OpenAI
import pytest
from talkie.audio_player import AudioPlayer
from talkie.cache import FileCache
from talkie.text_to_speech import TextToSpeech


@pytest.fixture
def temp_dir() -> Iterable[str]:
    """Create temporary directory for cache."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


def test_speak_calls_openai_and_sends_to_audio_player(temp_dir: str):
    """Test that speak() calls OpenAI API and sends audio data to AudioPlayer."""
    # Mock AudioPlayer
    audio_player = Mock(spec_set=AudioPlayer)

    # Mock OpenAI client and response
    openai_client = Mock(spec_set=OpenAI)
    response = Mock()
    response.content = b"fake_audio_data"
    openai_client.audio.speech.create.return_value = response

    # Set up cache mock to return None (cache miss - caches nothing)
    cache = Mock(spec_set=FileCache)
    cache.get.return_value = None

    # Create TextToSpeech instance
    tts = TextToSpeech(
        audio_player=audio_player,
        cache=cache,
        open_ai=openai_client,
        voice="alloy",
        model="tts-1",
    )

    # Call speak with test text
    test_text = "Hello, world!"
    tts.speak(test_text)

    # Give the worker thread time to process
    time.sleep(0.1)

    # Verify OpenAI API was called with correct parameters
    openai_client.audio.speech.create.assert_called_once_with(
        model="tts-1", voice="alloy", input=test_text
    )

    # Verify audio data was cached
    cache.add.assert_called_once_with(test_text, b"fake_audio_data")

    # Verify audio data was sent to AudioPlayer
    audio_player.put_audio.assert_called_once_with(b"fake_audio_data")

    tts.stop_all()
    tts.stop_playing()
    tts.clear_all()
    tts.cleanup()

    audio_player.stop_all.assert_called()
    audio_player.stop_playing.assert_called()
    audio_player.clear_all.assert_called()
