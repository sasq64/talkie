#!/usr/bin/env python
import argparse
import logging
from pathlib import Path
import pixpy as pix
import yaml

from utils.wrap import wrap_lines
from ai_player import AIPlayer, TextOutput, ImageOutput, PromptOutput


def main():
    prompts: dict[str, str] = yaml.safe_load(open("prompts.yaml"))

    parser = argparse.ArgumentParser(description="Talkie - AI Interactive Fiction player")
    _ = parser.add_argument("-g", "--game", type=str, default="curses.z5",
                      help="Game file to load")
    args = parser.parse_args()

    logging.getLogger().setLevel(logging.INFO)

    # Initialize pixpy rendering components
    screen = pix.open_display(size=(1280, 1024))
    tile_set = pix.TileSet(font_file="3270.ttf", size=32)
    con_size = (screen.size / tile_set.tile_size).toi()
    console = pix.Console(tile_set=tile_set, cols=con_size.x, rows=con_size.y)

    # Initialize AI player
    ai_player = AIPlayer(prompts, Path(args.game))
    current_image: None | pix.Image = None

    console.read_line()

    while pix.run_loop():
        screen.draw(drawable=console, top_left=(0, 0), size=console.size)

        # Handle keyboard input
        if pix.was_pressed(pix.key.ESCAPE):
            ai_player.stop_playing()
        if pix.is_pressed(pix.key.F5):
            screen.draw_color = pix.color.LIGHT_GREEN
            screen.filled_circle(center=(20, 20), radius=18)
            screen.draw_color = pix.color.WHITE
            ai_player.start_voice_recording()
        elif ai_player.recording:
            ai_player.end_voice_recording()


        # Process game output
        ai_player.update()
        output = ai_player.get_next_output()
        if output:
            if isinstance(output, ImageOutput):
                current_image = pix.load_png(output.file_name)
            elif isinstance(output, PromptOutput):
                console.cancel_line()
                console.write(output.text + "\n")
                console.read_line()
            elif isinstance(output, TextOutput):
                if console.reading_line:
                    console.cancel_line()
                console.write("\n")
                for line in wrap_lines(output.text.splitlines(), console.grid_size.x - 1):
                    console.write(line + "\n")
                console.write("\n>")
                console.read_line()

        # Handle text input events
        for e in pix.all_events():
            if isinstance(e, pix.event.Key):
                current_image = None

            if isinstance(e, pix.event.Text):
                console.set_color(pix.color.LIGHT_BLUE, pix.color.BLACK)
                console.write(e.text)
                console.set_color(pix.color.WHITE, pix.color.BLACK)

                if e.text[0] == "/":
                    cmd = e.text[1:].strip()
                    print(cmd)
                    image_path = ai_player.handle_slash_command(cmd)
                    if image_path:
                        current_image = pix.load_png(image_path)
                else:
                    ai_player.stop_audio()
                    ai_player.write_command(e.text)
                console.read_line()

        # Render current image overlay
        if current_image:
            screen.draw_color = 0x00000080
            screen.filled_rect(top_left=(0, 0), size=screen.size)
            screen.draw_color = pix.color.WHITE
            sz = current_image.size / 2
            xy = (screen.size - sz) / 2
            screen.draw(current_image, top_left=xy, size=sz)
        screen.swap()


if __name__ == "__main__":
    main()
