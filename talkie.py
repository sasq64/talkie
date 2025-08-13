from concurrent.futures import Future
import pixpy as pix
import subprocess
import threading
import queue
import re

from tts_handler import TTSHandler
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
            if remaining_text[match.start():match.end() + 1].endswith('\n'):
                match_text += '\n'
            remaining_text = remaining_text.replace(match_text, '', 1).strip()
        else:
            result[name] = ''
    
    result['text'] = remaining_text
    return result
    
def parse_adventure_description(text: str) -> dict[str, str]:
    return parse_text(text, 
        { "title": r"^(.*)\s{5,}(.*)$",
        "header": r"^Using normal.*\nLoading.*$",
        "trademark": r"^.*trademark.*nfocom.*$",
        "release": r"^Release.*Serial.*$",
         "prompt": r"\n+>",
         "copyright": r"^Copyright (.*)" },
        )



def main():
    screen = pix.open_display(size=(1280,720))
    console = pix.Console(cols=1280//16, rows=720//32)
    tts = TTSHandler()

    voice = VoiceToText()
    desc = ""

    # To deal with permission
    voice.record_audio(0.1)

    proc = subprocess.Popen(['dfrotz', '-m', '-w', '1000', './anchor.z8'],
                           stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)

    output_queue : queue.Queue[bytes] = queue.Queue()

    def read_output():
        if proc.stdout:
            while True:
                data = proc.stdout.read1(1024)
                if not data:
                    break
                output_queue.put(data)

    output_thread = threading.Thread(target=read_output, daemon=True)
    output_thread.start()

    console.read_line()
    recording = False
    vtt_future: Future[str] | None = None
    while pix.run_loop():
        screen.draw(drawable=console, top_left=(0,0), size=screen.size)
        if pix.is_pressed(pix.key.F5):
            screen.filled_circle(center=(10,10), radius=8)
            if not recording:
                voice.start_transribe()
                recording = True
        elif recording:
            vtt_future = voice.end_transcribe(prompt=
                    f"""
The following recording is a single sentence command to control text adventure or interactive fiction story.
It is usually in the form <verb> <noun> or <verb> <noun> <preposition> <noun>.

Common commands
- Look, examine <object>
- go north / south / east / west
- drop sword, take scroll

This is the current situation to which the command probably relates:
```
{desc}
```
""")
            recording = False

        if vtt_future is not None and vtt_future.done():
            text = vtt_future.result()
            vtt_future = None
            print(f"'{text}'")
            text += "\n"
            if proc.stdin is not None:
                console.cancel_line()
                console.write(text)
                _ = proc.stdin.write(text.encode())
                proc.stdin.flush()
                console.read_line()

        try:
            text = output_queue.get_nowait()
            decoded_text = text.decode()
            stripped = "\n".join([line.strip() for line in decoded_text.splitlines()])
            print(f"STDIO:'{stripped}'")
            fields = parse_adventure_description(stripped)
            print(fields)
            desc = fields["text"]
            tts.speak(desc)
            if console.reading_line:
                console.cancel_line()
            console.write(stripped)
            console.read_line()
        except queue.Empty:
            pass

        for e in pix.all_events():
            if isinstance(e, pix.event.Text):
                if proc.stdin is not None:
                    print(f"'{e.text}'")
                    _ = proc.stdin.write(e.text.encode())
                    proc.stdin.flush()
                    console.read_line()

        screen.swap()

if __name__ == "__main__":
    main()

