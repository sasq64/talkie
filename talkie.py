from concurrent.futures import Future
import logging
from pathlib import Path
import pixpy as pix
import re

from utils.wrap import wrap_lines
from text_to_speech import TextToSpeech
from voice_recorder import VoiceToText
from if_player import IFPlayer
from image_gen import ImageGen
from text_utils import parse_adventure_description, unwrap_text, trim_lines

image_prompt = "Following is a description of a scene from a interactive fiction (text adventure). Generate an image to go with it. Use a 80s retro semi realistic style. Don't include too many details. NOTE: *Dont* include distinct objects in the foreground that are not part of the description. *Dont* include text from the description in the image.\n```\n{text}\n```"

whisper_prompt = """
The following recording is a single sentence command to control text adventure or interactive fiction story.
It is usually in the form <verb> <noun> or <verb> <noun> <preposition> <noun>.

Common commands
- Look, examine <object>
- go north / south / east / west
- drop sword, take scroll

This is the current situation to which the command probably relates:
```
{text}
```
"""


def main():

    logging.getLogger().setLevel(logging.INFO)
    screen = pix.open_display(size=(1280, 1024))
    tile_set = pix.TileSet(font_file="3270.ttf", size = 32)
    con_size = (screen.size / tile_set.tile_size).toi()
    console = pix.Console(tile_set=tile_set, cols=con_size.x, rows=con_size.y)

    tts = TextToSpeech(voice="alloy")
    voice = VoiceToText()
    desc = ""
    fields: dict[str, str] = {}

    # To deal with permission
    # voice.record_audio(0.1)

    player = IFPlayer(Path("curses.z5"))
    current_image : None | pix.Image = None

    image_gen = ImageGen()

    console.read_line() 
    recording = False
    vtt_future: Future[str] | None = None
    pattern = re.compile(r"[.?!>:]$")
    while pix.run_loop():
        screen.draw(drawable=console, top_left=(0, 0), size=console.size)
        if pix.was_pressed(pix.key.ESCAPE):
            tts.stop_playing()
        if pix.is_pressed(pix.key.F5):
            screen.draw_color = pix.color.LIGHT_GREEN
            screen.filled_circle(center=(20, 20), radius=18)
            screen.draw_color = pix.color.WHITE
            if not recording:
                voice.start_transribe()
                recording = True
        elif recording:
            vtt_future = voice.end_transcribe(prompt=whisper_prompt.format(**fields))
            recording = False

        if vtt_future is not None and vtt_future.done():
            text = vtt_future.result()
            vtt_future = None
            text += "\n"
            console.cancel_line()
            console.write(text)
            player.write(text)
            console.read_line()

        text = player.read()
        if text:
            text = trim_lines(text)
            text = unwrap_text(text)
            fields = parse_adventure_description(text)
            desc = fields["text"]
            for paragraph in desc.split("\n\n"):
                if len(paragraph.strip()) > 0:
                    if not pattern.search(paragraph):
                        paragraph += ". "
                        paragraph = paragraph.replace("ZORK I", "ZORK ONE").replace("A N C H O R H E A D", "### ANCHORHEAD")
                    tts.speak(paragraph)
            if console.reading_line:
                console.cancel_line()
            console.write("\n")
            for line in wrap_lines(desc.splitlines(), console.grid_size.x - 1):
                console.write(line + "\n")
            console.write("\n>")
            console.read_line()
            image_file = image_gen.get_image(image_prompt.format(**fields))
            if image_file:
                current_image = pix.load_png(image_file)

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
                    if cmd == "image":
                        image = image_gen.generate_image(image_prompt)
                        current_image = pix.load_png(image)
                else:
                    tts.stop_all()
                    player.write(e.text)
                console.read_line()

        if current_image:
            screen.draw_color = 0x00000080
            screen.filled_rect(top_left=(0,0), size=screen.size)
            screen.draw_color = pix.color.WHITE
            sz = current_image.size / 2
            xy = (screen.size - sz) / 2
            screen.draw(current_image, top_left=xy, size=sz)
        screen.swap()


if __name__ == "__main__":
    main()
