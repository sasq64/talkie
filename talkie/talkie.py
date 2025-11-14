#!/usr/bin/env python
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import Final
from array import array

import pixpy as pix

from .ai_player import AIPlayer, ImageOutput, PromptOutput, TextOutput
from .layout import Layout, Rectangle
from .scanlines import make_scanline_texture
from .talkie_config import TalkieConfig
from .upscale import Upscaler
from .utils.nerd import Nerd
from .utils.wrap import wrap_array, wrap_lines


def invert(color: int) -> int:
    return (0xFFFFFF00 - (color & 0xFFFFFF00)) | (color & 0xFF)


class Drawable:
    def __init__(
        self,
        rect: Rectangle,
        draw_cb: Callable[[pix.Canvas, pix.Float2, pix.Float2], None],
    ):
        self.rect = rect
        self.visible = True
        self.draw_cb = draw_cb
        self.color = pix.color.WHITE

    def draw(
        self,
        screen: pix.Canvas,
        xy: pix.Float2 | None = None,
        size: pix.Float2 | None = None,
    ):
        if not self.visible:
            return
        xy = xy or pix.Float2(self.rect.x, self.rect.y)
        size = size or pix.Float2(self.rect.width, self.rect.height)
        screen.draw_color = self.color
        self.draw_cb(screen, xy, size)


class Talkie:
    def __init__(
        self,
        screen: pix.Screen,
        config: TalkieConfig,
        ai_player: AIPlayer,
    ):
        self.screen: Final = screen
        data = resources.files("talkie.data")
        font_path = config.text_font or data / "3270.ttf"
        self.font = pix.load_font(str(font_path))
        self.text_size = config.text_size
        self.tile_set = pix.TileSet(font=self.font, size=config.text_size)

        self.config = config
        self.margins: list[float] = [0, 0.02, 0.05, 0.1, 0.2]
        self.key_mode = False

        self.bg: pix.Image | None = None
        if config.background_image:
            self.bg = pix.load_png(config.background_image)

        self.prefix = self.edit_prefix = ">"
        self.text_color = (config.text_color << 8) | 0xFF
        self.input_color = (config.input_color << 8) | 0xFF
        self.input_bgcolor = (config.input_bgcolor << 8) | 0xFF
        self.background_color = (config.background_color << 8) | 0x00
        self.border_color = (config.border_color << 8) | 0xFF
        self.input_box_color = (config.input_box_color << 8) | 0xFF

        if self.bg and self.background_color == 0xFF:
            self.background_color = 0x505050FF

        self.upscaler = Upscaler()

        self.border = pix.Float2(config.border_size, config.border_size)

        print(config.layout)
        self.layout = Layout(config.layout)
        self.console = pix.Console(tile_set=self.tile_set, cols=10, rows=10)
        self.input_console: pix.Console = pix.Console(
            tile_set=self.tile_set, cols=10, rows=1
        )

        self.lines: list[array[int]] = []
        # self.lines: list[str] = []
        self.top: int = 0

        self.do_layout()

        font = pix.load_font(str(data / "SymbolsNerdFont-Regular.ttf"))
        sz = pix.Float2(48, 48)
        self.mic_icon: Final = pix.Image(sz)
        self.mic_icon.draw_color = 0x2020A0FF
        self.mic_icon.filled_circle(center=sz / 2, radius=sz.x / 2 - 1)
        icon = font.make_image(chr(Nerd.nf_fa_microphone_lines), 32)
        self.mic_icon.draw_color = 0xFFFFFFFF
        self.mic_icon.draw(icon, center=sz / 2)

        self.ai_player: Final = ai_player
        self.current_image: None | pix.Image = None
        self.input_console.read_line()

    def do_layout(self):

        fh = self.tile_set.tile_size.y
        self.layout.set_size("input", height=fh)

        scale = self.config.scale
        w, h = (self.screen.size // scale).toi()
        self.rects = self.layout.layout(w, h)
        self.items: dict[str, Rectangle] = {}

        for r in self.rects:
            self.items[r.name] = r
            # print(r)

        self.drawables: list[Drawable] = []

        mi = self.items["input"]
        con_size = pix.Int2(mi.width, mi.height) // self.tile_set.tile_size
        edit_line = self.input_console.edit_line
        edit_pos = self.input_console.edit_pos
        self.input_console.cancel_line()
        self.input_console = pix.Console(
            tile_set=self.tile_set, cols=con_size.x, rows=1
        )
        self.input_console.cursor_color = (self.config.cursor_color << 8) | 0xFF

        self.pane_drawable: Drawable | None = None
        if "pane" in self.items:
            lw = self.config.input_box_line
            self.screen.line_width = lw
            d = Drawable(
                self.items["pane"], lambda s, xy, sz: s.rect(xy, sz - (lw, lw))
            )
            d.color = self.input_box_color
            self.drawables.append(d)
            self.pane_drawable = self.drawables[-1]

        mi = self.items["main"]
        print(f"MAIN SIZE {mi}")
        con_size = pix.Int2(mi.width, mi.height) // self.tile_set.tile_size
        self.console = pix.Console(
            tile_set=self.tile_set, cols=con_size.x, rows=con_size.y
        )

        self.console.autoscroll = False
        self.console.set_color(self.text_color, self.background_color)
        self.console.clear()
        self.console.cursor_color = (self.config.cursor_color << 8) | 0xFF

        self.input_console.set_color(self.input_color, self.input_bgcolor)
        self.input_console.clear()
        self.input_console.cursor_pos = (0, 0)
        self.input_console.cursor_on = True
        self.input_console.read_line()
        self.input_console.set_line(edit_line)
        self.input_console.edit_pos = edit_pos

        self.drawables.append(
            Drawable(
                self.items["input"],
                lambda s, xy, _: s.draw(
                    self.input_console, xy - (2, 2), self.input_console.size
                ),
            )
        )
        self.input_drawable = self.drawables[-1]

        self.refresh()

        self.drawables.append(
            Drawable(
                self.items["main"],
                lambda s, xy, _: s.draw(self.console, xy, self.console.size),
            )
        )
        self.canvas = pix.Image(size=self.screen.size // scale)

        self.scan_lines: pix.Image | None = None
        if self.config.use_scanlines:
            height = int(self.screen.size.y)
            img = make_scanline_texture(
                height, dark=0, pitch=scale, offset=0, soft=True
            )
            self.scan_lines = pix.Image(
                1,
                [
                    pix.blend_color(pix.color.BLACK, pix.color.WHITE, t) | 0xFF
                    for t in img
                ],
            )

        self.input_drawable.visible = not self.key_mode
        if self.pane_drawable:
            self.pane_drawable.visible = not self.key_mode

    def close(self):
        self.ai_player.close()

    def toggle_image(self):
        imgc = self.layout.find("imgcontainer")
        if imgc:
            a = imgc.attributes.get("nospace")
            if a == "true":
                imgc.attributes["nospace"] = "false"
            else:
                imgc.attributes["nospace"] = "true"
            self.do_layout()

    def render_game_image(self):
        if not self.current_image:
            return

        c = self.items.get("imgcontainer")
        # if c:
        #     self.screen.draw_color = 0x00000080
        #     self.screen.filled_rect(top_left=(c.x, c.y), size=(c.width, c.height))
        #     self.screen.draw_color = pix.color.WHITE
        img = self.items.get("image")
        if img:
            sz = self.current_image.size
            while sz.y * 2 < img.height and sz.x * 2 < img.width:
                sz *= 2
            while sz.y > img.height and sz.x < img.width:
                sz /= 2
            xy = pix.Float2(img.x, img.y)
            isize = pix.Float2(img.width, img.height)
            xy += (isize - sz) / 2
            self.screen.draw(self.current_image, top_left=xy, size=sz)

    def update(self):

        km = self.ai_player.key_mode()
        if km != self.key_mode:
            self.key_mode = km
            self.input_drawable.visible = not km
            if self.pane_drawable:
                self.pane_drawable.visible = not km

        self.upscaler.check_upscale()
        if self.bg:
            self.screen.draw_color = self.background_color
            self.screen.draw(self.bg, top_left=(0, 0), size=self.screen.size)
            self.screen.draw_color = 0xFFFF_FFFF
        else:
            self.screen.clear(self.background_color)
        self.canvas.clear(self.border_color)
        for drawable in self.drawables:
            drawable.draw(self.canvas)
        self.screen.draw(self.canvas, size=self.screen.size)

        # Handle keyboard input
        if pix.was_pressed(pix.key.ESCAPE):
            self.ai_player.stop_playing()
        if pix.is_pressed(pix.key.F5):
            self.screen.draw(self.mic_icon, (10, 10))
            self.ai_player.start_voice_recording()
        elif self.ai_player.recording:
            self.ai_player.end_voice_recording()

        # Render current image overlay
        self.render_game_image()

        if self.scan_lines:
            self.screen.blend_mode = pix.BLEND_MULTIPLY
            self.screen.draw(self.scan_lines, top_left=(0, 0), size=self.screen.size)
            self.screen.blend_mode = pix.BLEND_NORMAL

        # Process game output
        self.ai_player.update()

        # if self.ai_player.key_mode() and self.console.reading_line:
        #    self.console.cancel_line()
        #    cp = self.console.cursor_pos
        #    self.console.clear_area(0, cp.y, self.console.grid_size.x, 1)
        # elif not self.ai_player.key_mode() and not self.console.reading_line:
        #     self.console.write("\n>")
        #     self.console.read_line()

        output = self.ai_player.get_next_output()
        if output:
            if isinstance(output, ImageOutput):
                self.current_image = pix.load_png(str(output.file_name))
            elif isinstance(output, PromptOutput):
                self.write(output.text + "\n")
            elif isinstance(output, TextOutput):
                self.write(output.text)

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
            fg = self.text_color
            bg = self.background_color
            for c in line:
                self.console.put(pos, c & 0xFFFFFFFF, (c >> 24) | 0xFF, bg)
                pos += (1, 0)
            pos = pos.with_x0 + (0, 1)

    def write(self, text: str, color: int | None = None):
        print(f"WRITE '{text}'")
        if color is None:
            color = self.text_color
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

    def ctrl_commands(self, key: str):
        if key == "-":
            self.text_size -= 2
            self.tile_set = pix.TileSet(font=self.font, size=self.text_size)
        elif key == "=" or key == "+":
            self.text_size += 2
            self.tile_set = pix.TileSet(font=self.font, size=self.text_size)
        elif key == "p":
            self.toggle_image()
        elif key == "l":
            self.background_color = invert(self.background_color)
            self.text_color = invert(self.text_color)
            self.input_color = invert(self.input_color)
            self.input_bgcolor = invert(self.input_bgcolor)
            self.border_color = invert(self.border_color)
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

        elif key == "m":
            self.margins = self.margins[1:] + self.margins[:1]
            m = int(self.margins[0] * self.screen.width)
            self.layout.set_size("left", m, None)
            self.layout.set_size("right", m, None)
        else:
            return
        self.do_layout()

    def update_events(self, events: list[pix.event.AnyEvent]):
        # Handle text input events
        for e in events:
            if isinstance(e, pix.event.Resize):
                self.do_layout()

            if isinstance(e, pix.event.Key):
                if e.mods:
                    self.ctrl_commands(chr(e.key))

                print(f"KEY {e.key}")
                if e.key == pix.key.ESCAPE:
                    self.current_image = None
                elif e.key < 0x1000 and self.key_mode:
                    self.ai_player.write_command(chr(e.key))

            if isinstance(e, pix.event.Text):
                print(f"TEXT {e.text}")
                # self.write("\n" + self.prefix)
                self.write(e.text, self.input_color)
                # self.console.cursor_pos = self.console.cursor_pos.with_x0
                # self.console.write(self.prefix)
                # self.console.set_color(self.input_color, self.background_color)
                # self.console.write(e.text)
                # self.console.set_color(self.text_color, self.background_color)

                if e.text[0] == "/":
                    cmd = e.text[1:].strip()
                    if cmd == "fast":
                        result = self.upscaler.fast_upscale(Path("game.png"))
                        if result:
                            self.current_image = result
                    else:
                        _ = self.ai_player.handle_slash_command(cmd)
                else:
                    self.ai_player.stop_audio()
                    self.ai_player.write_command(e.text)
                if self.input_console:
                    self.input_console.read_line()
                else:
                    self.console.read_line()
