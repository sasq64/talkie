#!/usr/bin/env python
import argparse
import logging
from importlib import resources
from pathlib import Path
from typing import Final

import pixpy as pix
import yaml

from .ai_player import AIPlayer, ImageOutput, PromptOutput, TextOutput
from .utils.wrap import wrap_lines


class Talkie:
    def __init__(
        self,
        screen: pix.Screen,
        game_path: Path,
    ):
        data = resources.files("talkie.data")
        prompts_path = data / "prompts.yaml"
        self.prompts: dict[str, str] = yaml.safe_load(prompts_path.open())

        self.screen: Final = screen
        font_path = data / "3270.ttf"
        tile_set = pix.TileSet(font_file=str(font_path), size=32)
        con_size = (screen.size / tile_set.tile_size).toi()
        self.console: Final = pix.Console(
            tile_set=tile_set, cols=con_size.x, rows=con_size.y
        )
        self.ai_player: Final = AIPlayer(self.prompts, game_path)
        self.current_image: None | pix.Image = None
        self.console.read_line()

    def update(self):
        self.screen.draw(drawable=self.console, top_left=(0, 0), size=self.console.size)

        # Handle keyboard input
        if pix.was_pressed(pix.key.ESCAPE):
            self.ai_player.stop_playing()
        if pix.is_pressed(pix.key.F5):
            self.screen.draw_color = pix.color.LIGHT_GREEN
            self.screen.filled_circle(center=(20, 20), radius=18)
            self.screen.draw_color = pix.color.WHITE
            self.ai_player.start_voice_recording()
        elif self.ai_player.recording:
            self.ai_player.end_voice_recording()

        # Render current image overlay
        if self.current_image:
            self.screen.draw_color = 0x00000080
            self.screen.filled_rect(top_left=(0, 0), size=self.screen.size)
            self.screen.draw_color = pix.color.WHITE
            sz = self.current_image.size / 2
            xy = (self.screen.size - sz) / 2
            self.screen.draw(self.current_image, top_left=xy, size=sz)

        # Process game output
        self.ai_player.update()
        output = self.ai_player.get_next_output()
        if output:
            if isinstance(output, ImageOutput):
                self.current_image = pix.load_png(output.file_name)
            elif isinstance(output, PromptOutput):
                self.console.cancel_line()
                self.console.write(output.text + "\n")
                self.console.read_line()
            elif isinstance(output, TextOutput):
                if self.console.reading_line:
                    self.console.cancel_line()
                self.console.write("\n")
                for line in wrap_lines(
                    output.text.splitlines(), self.console.grid_size.x - 1
                ):
                    self.console.write(line + "\n")
                self.console.write("\n>")
                self.console.read_line()

    def update_events(self, events: list[pix.event.AnyEvent]):
        # Handle text input events
        for e in events:
            if isinstance(e, pix.event.Key):
                self.current_image = None

            if isinstance(e, pix.event.Text):
                self.console.set_color(pix.color.LIGHT_BLUE, pix.color.BLACK)
                self.console.write(e.text)
                self.console.set_color(pix.color.WHITE, pix.color.BLACK)

                if e.text[0] == "/":
                    cmd = e.text[1:].strip()
                    print(cmd)
                    self.ai_player.handle_slash_command(cmd)
                else:
                    self.ai_player.stop_audio()
                    self.ai_player.write_command(e.text)
                self.console.read_line()


def main():
    parser = argparse.ArgumentParser(
        description="Talkie - AI Interactive Fiction player"
    )
    _ = parser.add_argument(
        "-g", "--game", type=str, default="curses.z5", help="Game file to load"
    )
    args = parser.parse_args()

    logging.getLogger().setLevel(logging.INFO)

    # Initialize pixpy rendering components
    screen = pix.open_display(size=(1280, 1024))

    # Initialize Talkie
    game_path = Path(args.game)
    talkie = Talkie(screen, game_path)

    while pix.run_loop():
        talkie.update()
        talkie.update_events(pix.all_events())
        screen.swap()


if __name__ == "__main__":
    main()
