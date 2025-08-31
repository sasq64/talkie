from dataclasses import dataclass, field
from pathlib import Path

from pixtools.text_to_speech import Voice


@dataclass
class TalkieConfig:
    game_file: Path
    """Game file to load"""

    gfx_path: Path | None = None
    voice: Voice | None = None
    """Turn on text to speech with the given voice"""

    full_screen: bool = False
    window_width: int = 1280
    window_height: int = 1024

    prompt_file: Path | None = None
    prompts: dict[str, str] = field(default_factory=dict, init=False)

    text_color: int = 0xFFFFFF
    background_color: int = 0x000000
    input_color: int = 0x8080FF
    input_bgcolor: int = 0x101070
    text_font: Path | None = None
    text_size: int = 32
    border_size: int = 0
    inline_input: bool = False
    use_scanlines: bool = False

    adventure_guy: bool = False
    """Use 'adventure guy' to interpret prompts using AI"""
