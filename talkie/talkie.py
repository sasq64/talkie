#!/usr/bin/env python
from collections.abc import Callable
from importlib import resources
from typing import Final

import pixpy as pix

from .ai_player import AIPlayer, ImageOutput, PromptOutput, TextOutput
from .layout import Layout, Rectangle
from .scanlines import make_scanline_texture
from .talkie_config import TalkieConfig
from .utils.nerd import Nerd
from .utils.wrap import wrap_lines


class Drawable:
    def __init__(
        self,
        rect: Rectangle,
        draw_cb: Callable[[pix.Screen, pix.Float2, pix.Float2], None],
    ):
        self.rect = rect
        self.draw_cb = draw_cb
        self.color = pix.color.WHITE

    def draw(
        self,
        screen: pix.Screen,
        xy: pix.Float2 | None = None,
        size: pix.Float2 | None = None,
    ):
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
        tile_set = pix.TileSet(font_file=str(font_path), size=config.text_size)
        print(tile_set.tile_size)

        ui = (
            config.layout
            or """
<window layout="vert">
  <border layout="vert">
    <main/>
    <pane border="10"><input/></pane>
  </border>
</window>
"""
        )
        print(ui)

        layout = Layout(ui)
        layout.set_size("input", height=tile_set.tile_size.y)
        w, h = screen.size.toi()
        self.rects = layout.layout(w, h)

        self.items: dict[str, Rectangle] = {}

        for r in self.rects:
            self.items[r.name] = r
            print(r)

        self.border = pix.Float2(config.border_size, config.border_size)

        self.prefix = self.edit_prefix = ">"
        self.text_color = (config.text_color << 8) | 0xFF
        self.input_color = (config.input_color << 8) | 0xFF
        self.input_bgcolor = (config.input_bgcolor << 8) | 0xFF
        self.background_color = (config.background_color << 8) | 0xFF
        self.border_color = (config.border_color << 8) | 0xFF
        self.input_box_color = (config.input_box_color << 8) | 0xFF

        self.drawables: list[Drawable] = []

        self.drawables.append(
            Drawable(self.items["border"], lambda s, xy, sz: s.filled_rect(xy, sz))
        )
        self.drawables[-1].color = self.border_color

        self.input_console: pix.Console | None

        if config.inline_input:
            self.input_console = None
        else:
            mi = self.items["input"]
            con_size = pix.Int2(mi.width, mi.height) // tile_set.tile_size
            input_console = pix.Console(tile_set=tile_set, cols=con_size.x, rows=1)

            lw = config.input_box_line
            self.screen.line_width = lw
            d = Drawable(
                self.items["pane"], lambda s, xy, sz: s.rect(xy, sz - (lw, lw))
            )
            d.color = self.input_box_color
            self.drawables.append(d)

            input_console.set_color(self.input_color, self.input_bgcolor)
            input_console.clear()
            self.drawables.append(
                Drawable(
                    self.items["input"],
                    lambda s, xy, sz: s.draw(
                        input_console, xy - (2, 2), input_console.size
                    ),
                )
            )
            self.input_console = input_console

        mi = self.items["main"]
        con_size = pix.Int2(mi.width, mi.height) // tile_set.tile_size
        self.console: Final = pix.Console(
            tile_set=tile_set, cols=con_size.x, rows=con_size.y
        )
        self.console.set_color(self.text_color, self.background_color)
        self.console.clear()
        self.drawables.append(
            Drawable(
                self.items["main"],
                lambda s, xy, sz: s.draw(self.console, xy, self.console.size),
            )
        )

        self.scan_lines: pix.Image | None = None
        if config.use_scanlines:
            height = int(screen.size.y)
            img = make_scanline_texture(height, dark=0.0, pitch=4, offset=0, soft=True)
            self.scan_lines = pix.Image(
                1,
                [
                    pix.blend_color(pix.color.BLACK, pix.color.WHITE, t) | 0xFF
                    for t in img
                ],
            )

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
        if self.input_console:
            self.input_console.read_line()
        else:
            self.console.read_line()

    def close(self):
        self.ai_player.close()

    def update(self):
        self.screen.clear(
            self.border_color
            if self.border > pix.Float2.ZERO
            else self.background_color
        )
        for drawable in self.drawables:
            drawable.draw(self.screen)

        # Handle keyboard input
        if pix.was_pressed(pix.key.ESCAPE):
            self.ai_player.stop_playing()
        if pix.is_pressed(pix.key.F5):
            self.screen.draw(self.mic_icon, (10, 10))
            self.ai_player.start_voice_recording()
        elif self.ai_player.recording:
            self.ai_player.end_voice_recording()

        # Render current image overlay
        if self.current_image:
            self.screen.draw_color = 0x00000080
            self.screen.filled_rect(top_left=(0, 0), size=self.screen.size)
            self.screen.draw_color = pix.color.WHITE
            sz = self.current_image.size
            while sz.y * 2 < 640:
                sz *= 2
            while sz.y > 640:
                sz /= 2
            xy = (self.screen.size - sz) / 2
            self.screen.draw(self.current_image, top_left=xy, size=sz)

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

    def write(self, text: str):
        reading_line = self.console.reading_line
        if reading_line:
            self.console.cancel_line()
        for line in wrap_lines(text.splitlines(), self.console.grid_size.x - 1):
            self.console.write(line + "\n")
        if reading_line:
            self.console.write("\n")
            self.console.cursor_pos = self.console.cursor_pos.with_x0
            self.console.write(self.edit_prefix)
            self.console.read_line()

    def update_events(self, events: list[pix.event.AnyEvent]):
        # Handle text input events
        for e in events:
            if isinstance(e, pix.event.Key):
                self.current_image = None
                if e.key < 0x1000 and self.ai_player.key_mode():
                    print("KEY")
                    self.ai_player.write_command(chr(e.key))

            if isinstance(e, pix.event.Text):
                self.console.cursor_pos = self.console.cursor_pos.with_x0
                self.console.write(self.prefix)
                self.console.set_color(self.input_color, self.background_color)
                self.console.write(e.text)
                self.console.set_color(self.text_color, self.background_color)

                if e.text[0] == "/":
                    cmd = e.text[1:].strip()
                    _ = self.ai_player.handle_slash_command(cmd)
                else:
                    self.ai_player.stop_audio()
                    self.ai_player.write_command(e.text)
                if self.input_console:
                    self.input_console.read_line()
                else:
                    self.console.read_line()
