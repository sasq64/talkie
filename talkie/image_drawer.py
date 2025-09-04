from dataclasses import dataclass, field
from logging import getLogger
from pathlib import Path
from typing import Literal, cast

from PIL import Image

from .draw import PixelCanvas

logger = getLogger(__name__)

Command = Literal[
    "line", "fill", "clear", "setcolor", "img", "pal", "pixels", "imgsize", "bitmap"
]


@dataclass
class Bitmap:
    width: int = 0
    height: int = 0
    palette: list[int] = field(default_factory=list[int])
    pixels: bytes = field(default_factory=bytes)


class ImageDrawer:
    def __init__(self):
        width, height = 160, 96
        self.pcanvas: PixelCanvas = PixelCanvas(width, height)
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
        self.bitmaps: list[Bitmap] = []

    def add_text_command(self, s: str) -> bool:
        parts = s.split()
        cmd, args = cast("Command", parts[0]), [int(s, 0) for s in parts[1:]]

        match cmd:
            case "img" if len(args) == 4:
                no = args[0]
                print(f"IMG {no}")
                while len(self.bitmaps) <= no:
                    self.bitmaps.append(Bitmap(args[1], args[2]))
                return False
            case "pal" if len(args) >= 1:
                no = args[0]
                print(f"PAL {no}")
                self.bitmaps[no].palette = args[1:]
                return False
            case "pixels" if len(args) >= 1:
                no = args[0]
                print(f"PIXELS {no}")
                self.bitmaps[no].pixels = bytes(args[1:])
                return False
            case "imgsize":
                self.pcanvas = PixelCanvas(*args)
                return False
            case "line":
                self.pcanvas.draw_line(*args)
            case "fill":
                self.pcanvas.flood_fill(*args)
            case "clear":
                self.pcanvas.clear(0)
            case "setcolor":
                col = (self.colors[args[1]] << 8) | 0xFF
                self.palette[args[0]] = col
            case "bitmap":
                no = args[0]
                if no >= len(self.bitmaps):
                    return False
                print(f"BITMAP {no}")
                # x, y = args[1], args[2]
                bmp = self.bitmaps[no]
                self.pcanvas = PixelCanvas(bmp.width, bmp.height)
                self.pcanvas.set_pixels(bmp.pixels)
                self.palette = [(c << 8) | 0xFF for c in self.bitmaps[no].palette]
            case _:
                logger.warning(f"Unhandled cmd '{s}'")
                return False
        return True

    def get_image(self) -> Path:
        # Create image directly from canvas array and palette
        w, h = self.pcanvas.width, self.pcanvas.height
        game_image = Image.new("RGBA", (w, h))

        # Convert palette indexes to RGBA tuples directly
        rgba_data: list[tuple[int, int, int, int]] = []
        for idx in self.pcanvas.array:
            p = self.palette[idx]
            rgba_data.append((p >> 24 & 0xFF, p >> 16 & 0xFF, p >> 8 & 0xFF, p & 0xFF))

        game_image.putdata(rgba_data)  # pyright: ignore[reportUnknownMemberType]
        png_path = Path("game.png")
        game_image.save(png_path)
        return png_path
