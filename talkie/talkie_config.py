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

    layout: str | None = None
    gfx_path: Path | None = None
    voice: Voice | None = None
    """Turn on text to speech with the given voice"""

    full_screen: bool = False
    window_width: int = 1280
    window_height: int = 1024

    prompt_file: Path | None = None
    prompts: dict[str, str] = field(default_factory=dict[str, str], init=False)

    text_color: int = HexInt(0xFFFFFF)
    background_color: int = HexInt(0x000000)
    input_color: int = HexInt(0x8080FF)
    input_bgcolor: int = HexInt(0x000000)
    input_box_color: int = HexInt(0x000000)
    input_box_line: int = 3
    text_font: Path | None = None
    text_size: int = 32
    border_size: int = 0
    border_color: int = HexInt(0x000000)
    inline_input: bool = False
    use_scanlines: bool = False

    adventure_guy: bool = False
    """Use 'adventure guy' to interpret prompts using AI"""
