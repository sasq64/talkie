import pytest
from pathlib import Path
from faster_whisper import WhisperModel

model = WhisperModel("medium", device="cpu", compute_type="int8")

def transcribe(file_name: str, **kwargs) -> str:
    """Transcribe audio file using Whisper model."""
    segments, info = model.transcribe(file_name, language="en", **kwargs)
    return "".join([s.text for s in segments])


class TestTranscription:
    """Test transcription of audio files in wavtest directory."""
    
    # Expected transcriptions for each wav file (initially empty strings)
    EXPECTED_TRANSCRIPTIONS = {
        "climb_tree.wav": "",
        "examine_grating.wav": "",
        "examine_path.wav": "",
        "examine_the_leaves.wav": "",
        "go_east.wav": "",
        "go_east2.wav": "",
        "go_north.wav": "",
        "go_south.wav": "",
        "go_south_bad.wav": "",
        "go_west.wav": "",
        "inventory.wav": "",
        "kill_troll.wav": "",
        "more_leaves.wav": "",
        "open_grating.wav": "",
        "open_window.wav": "",
        "read_scroll.wav": "",
        "take_leaves.wav": "",
    }
    
    def check(self, wav_file : str, expected: str, context: str | None = None):
        """Test transcription of a specific wav file against expected output."""
        wav_path = Path("wavtest") / wav_file
        
        # Ensure the wav file exists
        assert wav_path.exists(), f"Audio file {wav_file} not found"
        
        prompt="""
Here follows the recording of a short english command for moving around or manipulating objects in a text adventure like Zork.

If the command is more than one word, the first word is *always* a verb.

If the command is two words, the second word is almost always a noun.

Examples: "go north", "examine sword", "inventory", "look", "take all from chest", "unlock door with key"
"""
        if context:
            prompt += f"\nThis is what the player just saw in the game, and what he might be referring to:\n```\n{context}\n```"
        # Transcribe the audio file
        actual = transcribe(
            str(wav_path),
            beam_size=5,
            vad_filter=True,
            patience=1.0,
            temperature=0.0,
            initial_prompt=prompt        )
        actual = actual.strip().lower()
        #if actual[-1] == ".":
        #    actual = actual[:-2]

        print(prompt)
        
        print(f"'{expected}' vs '{actual}'")
        # Compare against expected transcription
        # assert actual == expected, (
        #     f"Transcription mismatch for {wav_file}:\n"
        #     f"Expected: '{expected}'\n"
        #     f"Actual: '{actual}'"
        # )
    
    def test_all_wav_files(self):
        """Verify that all expected wav files exist in the wavtest directory."""
        wavtest_dir = Path("wavtest")
        assert wavtest_dir.exists(), "wavtest directory not found"

        self.check("examine_the_leaves.wav", "examine the leaves", "I can see:\nA pile of leaves.\n")
        #self.check("climb_tree.wav", "climb tree", "You can see a large tree.")
        self.check("inventory.wav", "inventory")
        #self.check("examine_grating.wav", "examine grating")
        self.check("open_window.wav", "open window")
        self.check("examine_path.wav", "examine path", "You are walking along a path.")
        self.check("kill_troll.wav", "kill troll")
        self.check("go_north.wav", "go north")

def main():
    tt = TestTranscription()
    tt.test_all_wav_files()
    
main()
