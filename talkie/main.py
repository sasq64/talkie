#!/usr/bin/env python
import logging
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import cast

import jsonargparse
import pixpy as pix
import yaml
from lagom import Container
from openai import OpenAI

from pixtools import ImageGen, OpenAIClient, TextToSpeech
from pixtools.cache import FileCache
from pixtools.openaiclient import GptModel
from talkie.adventure_guy import AdventureGuy
from talkie.if_player import IFPlayer
from talkie.image_drawer import ImageDrawer
from talkie.talkie import Talkie

from .talkie_config import TalkieConfig


@dataclass
class Resolver:
    parent: Container
    c: Container

    def setup[T](self, typ: type[T]):
        self.c[typ] = typ
        self.parent[typ] = lambda: self.c.resolve(typ)


def bind[T](self: Container, typ: type[T], t: T) -> Resolver:
    cc = self.clone()
    cc[typ] = t
    return Resolver(self, cc)


logger = logging.getLogger()


def main():
    # args = tyro.cli(TalkieConfig)
    jsonargparse.set_parsing_settings(docstring_parse_attribute_docstrings=True)

    args = cast(
        "TalkieConfig",
        jsonargparse.auto_cli(TalkieConfig, as_positional=True, parser_mode="toml"),  # pyright: ignore[reportUnknownMemberType]
    )

    # Initialize pixpy rendering components
    screen = pix.open_display(
        size=(args.window_width, args.window_height), full_screen=args.full_screen
    )

    logger.info("Starting game")

    data = resources.files("talkie.data")
    prompts_path = args.prompt_file or data / "prompts.yaml"
    args.prompts = yaml.safe_load(prompts_path.open())

    container = Container()
    container[TalkieConfig] = args
    container[pix.Screen] = screen

    # Load OpenAI API key
    api_key = ""
    key_path = Path.home() / ".openai.key"
    if key_path.exists():
        with open(key_path) as f:
            api_key = f.read().strip()
    client = OpenAI(api_key=api_key)
    container[OpenAI] = client

    img_cache = FileCache(Path(".cache/img"))
    tts_cache = FileCache(Path(".cache/tts"))

    container[GptModel] = GptModel.GPT4

    if args.adventure_guy:
        container[AdventureGuy] = lambda c: AdventureGuy(
            c[OpenAIClient], prompt=args.prompts["talk_prompt"]
        )
    else:
        container[AdventureGuy] = lambda c: None  # type: ignore[assignment]
    container[IFPlayer] = lambda c: IFPlayer(
        c[ImageDrawer], c[TalkieConfig].game_file, c[TalkieConfig].gfx_path
    )
    bind(container, FileCache, img_cache).setup(ImageGen)
    voice = args.voice
    if voice is not None:
        bind(container, FileCache, tts_cache).setup(TextToSpeech)
    else:
        container[TextToSpeech] = lambda c: None  # type: ignore[assignment]

    talkie = container[Talkie]

    while pix.run_loop():
        talkie.update()
        talkie.update_events(pix.all_events())
        screen.swap()
    talkie.close()


if __name__ == "__main__":
    main()
