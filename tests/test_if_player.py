import time
from pathlib import Path
from unittest.mock import Mock

import pytest
from talkie.if_player import IFPlayer
from talkie.image_drawer import ImageDrawer


def test_zork_basic_gameplay():
    """Test IFPlayer with Zork: start game, read initial text, send command, verify response."""
    game_path = Path(__file__).parent.parent / "games" / "zork.z3"

    if not game_path.exists():
        pytest.skip(f"Zork game file not found at {game_path}")

    image_drawer = Mock(spec_set=ImageDrawer)

    with IFPlayer(image_drawer, game_path) as player:
        # Wait for initial game output and read it
        max_attempts = 20
        result = None

        for _ in range(max_attempts):
            result = player.read()
            if result and hasattr(result, "text"):
                break
            time.sleep(0.1)

        assert result is not None, "Failed to get initial game output"
        assert hasattr(result, "text"), "Result should have 'text' attribute"

        initial_text = str(result.text)
        assert "West of House" in initial_text, (
            f"Expected 'West of House' in initial text, got: {initial_text}"
        )

        # Send command to open mailbox
        player.write("open mailbox\n")
        player.write("open mailbox\n")

        # Wait for and read response
        response = None
        for _ in range(max_attempts):
            response = player.read()
            if response and hasattr(response, "text"):
                break
            time.sleep(0.1)
        assert response
        assert "reveals a leaflet" in response.text
        assert "Score:" not in response.text

        assert response is not None, (
            "Failed to get response to 'open mailbox' command"
        )

        # Get transcript and verify mailbox interaction is recorded
        transcript = player.get_transcript()
        assert "open mailbox" in transcript, (
            f"Command 'open mailbox' not found in transcript: {transcript}"
        )
        assert "mailbox" in transcript.lower(), (
            f"'mailbox' not found in transcript: {transcript}"
        )
