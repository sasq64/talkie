from dataclasses import dataclass, field
from pathlib import Path

from pixtools.text_to_speech import Voice


class HexInt(int):
    def __repr__(self) -> str:  # used in help default printing
        return f"{int(self):06x}"

    __str__ = __repr__  # (optional) for symmetry


@dataclass
class TalkieConfig:
    game_file: Path
    """Game file to load"""

    gfx_path: Path | None = None
    """Path to graphics data, for games that use it"""

    voice: Voice | None = None
    """Turn on text to speech with the given voice"""

    full_screen: bool = False
    window_width: int = 1280
    window_height: int = 1024

    layout: str | None = None
    """XML description of screen layout"""

    prompt_file: Path | None = None
    """yaml file with AI prompt data"""

    prompts: dict[str, str] = field(default_factory=dict[str, str])

    text_color: int = HexInt(0xFFFFFF)
    background_color: int = HexInt(0x000000)
    input_color: int = HexInt(0x8080FF)
    input_bgcolor: int = HexInt(0x000000)
    input_box_color: int = HexInt(0x000000)
    border_color: int = HexInt(0x000000)

    input_box_line: int = 3
    """Width of bottom read line box"""

    text_font: Path | None = None
    text_size: int = 32
    border_size: int = 0
    inline_input: bool = False
    """Read input inline with text (oldschool) instead of bottom of screen"""
    use_scanlines: bool = False

    adventure_guy: bool = False
    """Use 'adventure guy' to interpret prompts using AI"""
