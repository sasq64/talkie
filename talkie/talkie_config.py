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

    gfx_path: Path | None = field(default=None, metadata={"aliases": ["-G"]})
    """Path to graphics data, for games that use it"""

    voice: Voice | None = None
    """Turn on text to speech with the given voice"""

    full_screen: bool = field(default=False, metadata={"aliases": ["-f"]})
    window_width: int = 1280
    window_height: int = 1024

    layout: str = ""
    """XML description of screen layout"""

    prompts: dict[str, str] = field(default_factory=dict[str, str])

    text_color: int = HexInt(0xFFFFFF)
    background_color: int = HexInt(0x000000)
    """Screen is cleared with this color (when there is no background)"""

    input_color: int = HexInt(0x8080FF)
    input_bgcolor: int = HexInt(0x000000)
    input_box_color: int = HexInt(0x000080)
    border_color: int = HexInt(0x000000)
    """The color of everything that is not a text area"""

    cursor_color: int = HexInt(0xE08030)

    background_image: Path | None = None
    tile_background: bool = False

    input_box_line: int = 4
    """Width of bottom read line box"""

    image_cache: Path | None = None

    scale: float = 1

    text_font: Path | None = None
    text_size: int = 28
    border_size: int = 8
    inline_input: bool = True
    """Read input inline with text (oldschool) instead of bottom of screen"""
    use_scanlines: bool = False

    adventure_guy: bool = False
    """Use 'adventure guy' to interpret prompts using AI"""
