import logging
import queue
import subprocess
import threading
from pathlib import Path

from .text_utils import parse_adventure_description, trim_lines, unwrap_text


class IFPlayer:
    def __init__(self, file_name: Path):
        # zcode = re.compile(r"\.z(ode|[123456789])$")
        self.proc = subprocess.Popen(
            ["dfrotz", "-m", "-w", "1000", file_name.as_posix()],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.output_queue: queue.Queue[bytes] = queue.Queue()
        self.transcript: list[tuple[str, str]] = []

        def read_output():
            if self.proc.stdout:
                while True:
                    data: bytes = self.proc.stdout.read1(16384)  # type: ignore
                    if not data:
                        break
                    logging.info(f"OUT: '{data.decode()}'")
                    self.output_queue.put(data)

        self.output_thread = threading.Thread(target=read_output, daemon=True)
        self.output_thread.start()

    def read(self) -> dict[str, str] | None:
        try:
            raw_text = self.output_queue.get_nowait()
            result = raw_text.decode()
            text = trim_lines(result)
            text = unwrap_text(text)
            fields = parse_adventure_description(text)
            print(f"### PARSED: '{text}' into:\n{fields}")
            self.transcript.append((":", fields["text"]))
            return fields
        except queue.Empty:
            pass
        return None

    def write(self, text: str):
        if self.proc.stdin is not None:
            logging.info(f"IN: '{text}'")
            _ = self.proc.stdin.write(text.encode())
            self.transcript.append((">", text))
            self.proc.stdin.flush()

    def get_transcript(self) -> str:
        lines: list[str] = []
        for c, line in self.transcript:
            if c == ">":
                lines.append("\n>" + line)
            else:
                lines.append(line)
        return "\n".join(lines)
