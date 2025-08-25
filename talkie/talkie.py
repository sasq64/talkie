#!/usr/bin/env python
import argparse
import logging
from importlib import resources
from pathlib import Path
from typing import Final

import pixpy as pix
import yaml
from lagom import Container
from openai import OpenAI

from talkie.adventure_guy import AdventureGuy
from talkie.audio_player import AudioPlayer
from talkie.cache import FileCache
from talkie.if_player import IFPlayer
from talkie.image_gen import ImageGen
from talkie.openaiclient import OpenAIClient
from talkie.text_to_speech import TextToSpeech

from .ai_player import AIPlayer, ImageOutput, PromptOutput, TextOutput
from .talkie_config import TalkieConfig
from .utils.nerd import Nerd
from .utils.wrap import wrap_lines

logger = logging.getLogger()


class Talkie:
    def __init__(
        self,
        screen: pix.Screen,
        config: TalkieConfig,
        ai_player: AIPlayer,
    ):
        print(config.game_file)

        self.screen: Final = screen
        # self.game_image: pix.Image = pix.Image(160, 128)
        data = resources.files("talkie.data")
        font_path = data / "3270.ttf"
        tile_set = pix.TileSet(font_file=str(font_path), size=32)
        con_size = (screen.size / tile_set.tile_size).toi()
        self.console: Final = pix.Console(
            tile_set=tile_set, cols=con_size.x, rows=con_size.y
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
        self.console.read_line()

    def close(self):
        self.ai_player.close()

    def update(self):
        self.screen.draw(drawable=self.console, top_left=(0, 0), size=self.console.size)

        # self.screen.draw(self.game_image, top_left=(50,50), size = self.game_image.size * (4,2))

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

        # Process game output
        self.ai_player.update()
        output = self.ai_player.get_next_output()
        if output:
            if isinstance(output, ImageOutput):
                # Load image - could be from image generation or graphics commands
                # if str(output.file_name) == "game.png":
                #    self.game_image = pix.load_png(str(output.file_name))
                # else:
                self.current_image = pix.load_png(str(output.file_name))
            elif isinstance(output, PromptOutput):
                self.console.cancel_line()
                self.console.write(output.text + "\n")
                self.console.read_line()
            elif isinstance(output, TextOutput):
                if self.console.reading_line:
                    self.console.cancel_line()
                    cp = self.console.cursor_pos
                    self.console.clear_area(0, cp.y, self.console.grid_size.x, 1)
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
                    _ = self.ai_player.handle_slash_command(cmd)
                else:
                    self.ai_player.stop_audio()
                    self.ai_player.write_command(e.text)
                self.console.read_line()


class Args(argparse.Namespace):
    game: Path | None = None
    gfx: Path | None = None


def main():
    parser = argparse.ArgumentParser(
        description="Talkie - AI Interactive Fiction player"
    )
    _ = parser.add_argument(
        "-g", "--game", type=Path, default="curses.z5", help="Game file to load"
    )
    _ = parser.add_argument(
        "-G", "--gfx", type=Path, default="curses.z5", help="Graphics file to load"
    )
    args = parser.parse_args(namespace=Args)
    assert args.game

    # Initialize pixpy rendering components
    screen = pix.open_display(size=(1280, 1024))

    logger.info("Starting game")
    # Initialize Talkie

    data = resources.files("talkie.data")
    prompts_path = data / "prompts.yaml"
    prompts: dict[str, str] = yaml.safe_load(prompts_path.open())

    container = Container()
    container[pix.Screen] = screen

    # Load OpenAI API key
    api_key = ""
    key_path = Path.home() / ".openai.key"
    if key_path.exists():
        with open(key_path) as f:
            api_key = f.read().strip()
    client = OpenAI(api_key=api_key)
    container[OpenAI] = client

    tts_cache = FileCache(Path(".cache/tts"))
    img_cache = FileCache(Path(".cache/img"))

    container[OpenAIClient] = lambda c: OpenAIClient(c[OpenAI], model="gpt4")
    # container[AdventureGuy] = lambda c: AdventureGuy(c[OpenAIClient], prompt="")
    container[AdventureGuy] = None
    container[TalkieConfig] = TalkieConfig(args.game, args.gfx, prompts)
    container[IFPlayer] = lambda c: IFPlayer(
        c[TalkieConfig].game_file, c[TalkieConfig].gfx_path
    )
    container[ImageGen] = lambda c: ImageGen(c[OpenAI], img_cache)
    container[TextToSpeech] = lambda c: TextToSpeech(
        c[AudioPlayer], tts_cache, c[OpenAI], voice="alloy"
    )

    talkie = container[Talkie]

    while pix.run_loop():
        talkie.update()
        talkie.update_events(pix.all_events())
        screen.swap()
    talkie.close()


if __name__ == "__main__":
    main()
