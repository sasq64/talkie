from array import array

import pixpy as pix

from talkie.utils.wrap import wrap_array


class LineConsole:
    def __init__(self, tile_set: pix.TileSet, cols: int, rows: int):
        self.tile_set = tile_set
        self.console = pix.Console(tile_set=self.tile_set, cols=cols, rows=rows)
        self.console.autoscroll = False
        self.lines: list[array[int]] = []
        self.top: int = 0
        self.fg_color = pix.color.WHITE
        self.bg_color = pix.color.BLACK

    @property
    def size(self):
        return self.console.size

    def resize(self, cols: int, rows: int):
        self.console = pix.Console(tile_set=self.tile_set, cols=cols, rows=rows)
        self.console.autoscroll = False
        self.refresh()

    def draw(self, screen: pix.Canvas, xy: pix.Float2, size: pix.Float2):
        screen.draw(self.console, xy, size)

    def reverse_color(self):
        new_lines: list[array[int]] = []
        for line in self.lines:
            nl = array(
                "Q",
                [
                    (i & 0xFFFFFFFF) | (0xFFFFFF00000000 - (i & 0xFFFFFF00000000))
                    for i in line
                ],
            )
            new_lines.append(nl)
        self.lines = new_lines

    def refresh(self):
        n = self.top
        y = 0
        self.console.clear()
        self.console.cursor_pos = (0, 0)
        w = self.console.grid_size.x - 1
        h = self.console.grid_size.y - 1
        lines: list[array[int]] = []
        n = len(self.lines) - 1
        print("## REFRESH")
        space = array("Q", [0x20])
        while n >= 0:
            line = self.lines[n]
            n -= 1
            screen_lines = wrap_array([line], w, space)
            screen_lines.reverse()
            for screen_line in screen_lines:
                lines.append(screen_line)
                y += 1
                if y >= h:
                    break
            if y >= h:
                break
        lines.reverse()
        pos = pix.Int2(0, 0)
        for line in lines:
            # self.console.set_color(self.text_color, self.background_color)
            bg = self.bg_color
            for c in line:
                self.console.put(pos, c & 0xFFFFFFFF, (c >> 24) | 0xFF, bg)
                pos += (1, 0)
            pos = pos.with_x0 + (0, 1)

    def write(self, text: str, color: int | None = None):
        print(f"WRITE '{text}'")
        if color is None:
            color = self.fg_color
        color = (color >> 8) << 32
        add = len(self.lines) > 0
        for line in text.splitlines():
            a = array("Q", [ord(c) | color for c in line])
            if add:
                self.lines[-1].extend(a)
                add = False
            else:
                self.lines.append(a)
        if text.endswith("\n"):
            self.lines.append(array("Q"))
        self.refresh()
