from dataclasses import dataclass
from pathlib import Path
from typing import Final

from PIL import Image

from .draw import PixelCanvas


@dataclass
class Line:
    x0: int
    y0: int
    x1: int
    y1: int
    col0: int
    col1: int


@dataclass
class Fill:
    x: int
    y: int
    col0: int
    col1: int


@dataclass
class SetColor:
    color: int
    index: int


@dataclass
class Clear:
    pass


@dataclass
class ShowBitmap:
    bitmap: int


@dataclass
class ImageInfo:
    no: int
    width: int
    height: int
    numcolors: int


@dataclass
class Palette:
    no: int
    colors: list[int]


@dataclass
class Pixels:
    no: int
    pixel_indices: list[int]  # List of palette indices


Command = Fill | Line | Clear | SetColor | ShowBitmap | ImageInfo | Palette | Pixels

# Registry mapping command names to (class, argument types)
COMMANDS: dict[str, tuple[type[Command], list[type]]] = {
    "line": (Line, [int, int, int, int, int, int]),
    "fill": (Fill, [int, int, int, int]),
    "clear": (Clear, []),
    "setcolor": (SetColor, [int, int]),
}


def parse_command(s: str) -> Command | None:
    parts = s.split()
    cmd, args = parts[0], parts[1:]

    # Handle special bitmap commands
    if cmd == "img" and len(args) == 4:
        return ImageInfo(int(args[0]), int(args[1]), int(args[2]), int(args[3]))
    elif cmd == "pal" and len(args) >= 1:
        no = int(args[0])
        colors: list[int] = []
        for color_str in args[1:]:
            colors.append(int(color_str, 0))
        return Palette(no, colors)
    elif cmd == "pixels" and len(args) >= 1:
        no = int(args[0])
        pixel_indices: list[int] = []
        for pixel_str in args[1:]:
            pixel_indices.append(int(pixel_str, 0))
        return Pixels(no, pixel_indices)

    if cmd not in COMMANDS:
        return None

    cls, types = COMMANDS[cmd]

    if len(args) != len(types):
        raise ValueError(f"Wrong number of arguments for {cmd}: {args}")

    # Convert arguments to expected types
    converted = [t(a) for t, a in zip(types, args, strict=False)]
    return cls(*converted)


class ImageDrawer:
    def __init__(self):
        width, height = 160, 96
        self.pcanvas: Final = PixelCanvas(width, height)
        self.commands: list[Command] = []
        self.colors: list[int] = [
            0,
            0xFF0000,
            0x30E830,
            0xFFFF00,
            0x0000FF,
            0xA06800,
            0x00FFFF,
            0xFFFFFF,
        ]
        self.palette: list[int] = [0] * 64

    def handle_gfx(self, gfx: list[Command]):
        """Handle graphics commands and return path to generated PNG file"""
        for cmd in gfx:
            if isinstance(cmd, Line):
                self.pcanvas.draw_line(
                    cmd.x0, cmd.y0, cmd.x1, cmd.y1, cmd.col0, cmd.col1
                )
            elif isinstance(cmd, Clear):
                self.pcanvas.clear(0)
            elif isinstance(cmd, SetColor):
                col = (self.colors[cmd.index] << 8) | 0xFF
                self.palette[cmd.color] = col
            elif isinstance(cmd, Fill):
                self.pcanvas.flood_fill(cmd.x, cmd.y, cmd.col0, cmd.col1)

    def add_text_command(self, command: str):
        cmd = parse_command(command)
        if cmd:
            self.commands.append(cmd)
            return True
        return False

    def flush(self):
        self.handle_gfx(self.commands)
        self.commands.clear()

    def get_image(self) -> Path:
        self.flush()

        # Create image directly from canvas array and palette
        w, h = self.pcanvas.width, self.pcanvas.height
        game_image = Image.new("RGBA", (w, h))

        # Convert palette indexes to RGBA tuples directly
        rgba_data: list[tuple[int, int, int, int]] = []
        for idx in self.pcanvas.array:
            p = self.palette[idx]
            rgba_data.append((p >> 24 & 0xFF, p >> 16 & 0xFF, p >> 8 & 0xFF, p & 0xFF))

        game_image.putdata(rgba_data)
        png_path = Path("game.png")
        game_image.save(png_path)
        return png_path
