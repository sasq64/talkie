from dataclasses import dataclass
from pathlib import Path


@dataclass
class TalkieConfig:
    game_file: Path
    gfx_path: Path | None
    prompts: dict[str, str]
