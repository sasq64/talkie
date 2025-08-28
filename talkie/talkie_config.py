from dataclasses import dataclass, field
from pathlib import Path

from talkie.text_to_speech import Voice


@dataclass
class TalkieConfig:
    game_file: Path
    """Game file to load"""

    gfx_path: Path | None = None
    voice: Voice | None = None
    """Turn on text to speech with the given voice"""

    full_screen: bool = False
    prompt_file: Path | None = None
    prompts: dict[str, str] = field(default_factory=dict, init=False)
    text_color: int = 0xFFFFFF
    background_color: int = 0x000000
    text_font: Path | None = None
