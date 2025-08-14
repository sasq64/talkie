from concurrent.futures import Future
import logging
from pathlib import Path
import pixpy as pix
import subprocess
import threading
import queue
import re

from utils.wrap import wrap_lines
from tts_handler import TextToSpeech
from voice_recorder import VoiceToText


def parse_text(text: str, patterns: dict[str, str]) -> dict[str, str]:
    """Parse a description by matching named regex patterns and removing matches from text.

    Args:
        text: The input text to parse
        patterns: Dict mapping names to regex patterns

    Returns:
        Dict with 'text' key containing remaining text and other keys for named matches
    """
    result = {}
    remaining_text = text

    for name, pattern in patterns.items():
        match = re.search(pattern, remaining_text, re.MULTILINE)
        if match:
            result[name] = match.group(0)
            # Remove the match and any trailing newline to avoid double newlines
            match_text = match.group(0)
            if remaining_text[match.start() : match.end() + 1].endswith("\n"):
                match_text += "\n"
            remaining_text = remaining_text.replace(match_text, "", 1).strip()
        else:
            result[name] = ""

    result["text"] = remaining_text
    return result


def parse_adventure_description(text: str) -> dict[str, str]:
    return parse_text(
        text,
        {
            "title": r"^(.*)\s{5,}(.*)$",
            "header": r"^Using normal.*\nLoading.*$",
            "trademark": r"^.*trademark.*nfocom.*$",
            "release": r"^Release.*Serial.*$",
            "prompt": r"\n+>",
            "copyright": r"^Copyright (.*)",
        },
    )

def unwrap_text(text: str, colum: int = 200) -> str:
    """
    Try to unwrap wrapped text. Assumes any line that is longer than 'column' and does not end in punctuation should be joined with the next line.
    """

    pattern = re.compile(r"[.?!>:]$")
    new_lines : list[str] = []
    last_line: str  = ""
    for line in text.splitlines():
        if len(line) > colum and not pattern.search(line):
            if last_line != "":
                last_line = last_line + " " + line
            else:
                last_line = line
        else:
            if last_line != "":
                new_lines.append(last_line + " " + line) 
                last_line = ""
            else:
                new_lines.append(line)
    if last_line != "":
        new_lines.append(last_line) 

    return "\n".join(new_lines)

def trim_lines(text: str) -> str:
    """Trim spaces from the beginning and end of all lines in 'text'"""
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(lines)

class IFPlayer:
    def __init__(self, file_name: Path):
        zcode = re.compile(r"\.z(ode|[123456789])$")
        self.proc = subprocess.Popen(
            ["dfrotz", "-m", "-w", "1000", file_name.as_posix()],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.output_queue: queue.Queue[bytes] = queue.Queue()

        def read_output():
            if self.proc.stdout:
                while True:
                    data : bytes = self.proc.stdout.read1(16384)  # type: ignore
                    if not data:
                        break
                    logging.info(f"OUT: '{data.decode()}'")
                    self.output_queue.put(data)

        self.output_thread = threading.Thread(target=read_output, daemon=True)
        self.output_thread.start()

    def read(self) -> str | None:
        try:
            text = self.output_queue.get_nowait()
            return text.decode()
        except queue.Empty:
            pass
        return None

    def write(self, text: str):
        if self.proc.stdin is not None:
            logging.info(f"IN: '{text}'")
            _ = self.proc.stdin.write(text.encode())
            self.proc.stdin.flush()


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
    screen = pix.open_display(size=(1280, 720))
    console = pix.Console(cols=1280 // 16, rows=720 // 32, font_size=20, font_file="3270.ttf")

    tts = TextToSpeech(voice="alloy")
    voice = VoiceToText()
    desc = ""
    fields: dict[str, str] = {}

    # To deal with permission
    # voice.record_audio(0.1)

    player = IFPlayer(Path("zork.z3"))

    console.read_line() 
    recording = False
    vtt_future: Future[str] | None = None
    pattern = re.compile(r"[.?!>:]$")
    while pix.run_loop():
        screen.draw(drawable=console, top_left=(0, 0), size=screen.size)
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

        for e in pix.all_events():
            if isinstance(e, pix.event.Text):
                player.write(e.text)
                console.read_line()

        screen.swap()


if __name__ == "__main__":
    main()
