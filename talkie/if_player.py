from importlib import resources
from logging import getLogger
import queue
import subprocess
import threading
import re
from pathlib import Path
from typing import Final, cast

from .text_utils import parse_adventure_description, trim_lines, unwrap_text

logger = getLogger(__name__)

class IFPlayer:
    def __init__(self, file_name: Path):
        zcode = re.compile(r"\.z(ode|[123456789])$")
        l9 = re.compile(r"\.l9$")
        data = resources.files("talkie.data")

        if zcode.search(file_name.name):
            args = ["dfrotz", "-m", "-w", "1000", file_name.as_posix()]
        elif l9.search(file_name.name):
            args = [str(data / "l9"), file_name.as_posix()]
        else:
            raise RuntimeError("Unknown format")
        print(args)

        self.proc : Final = subprocess.Popen(
            args,
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
                    self.output_queue.put(data)

        self.output_thread: Final  = threading.Thread(target=read_output, daemon=True)
        self.output_thread.start()

    def read(self) -> dict[str, str] | None:
        meta = re.compile(r"#\[(.*)\]#")
        try:
            raw_text = self.output_queue.get_nowait()
            result = raw_text.decode()
            text = trim_lines(result)
            for line in text.splitlines():
                if meta.search(line):
                    # TODO parse meta command here
                    pass
            text = meta.sub("", text)

            text = unwrap_text(text)
            ps = text.split("\n\n")
            if len(ps) > 1:
                first = ps[0].strip()
                for px in ps[1:]:
                    if px.splitlines()[0].strip() == first:
                        logger.debug(f"Dropping first line '{first}'")
                        _ = ps.pop(0)
                        break
                text = "\n\n".join(ps)
            fields = parse_adventure_description(text)
            logger.debug(f"Parsed: '{text}' into:\n{fields}")
            self.transcript.append((":", fields["text"]))
            fields["full_text"] = result
            return fields
        except queue.Empty:
            pass
        return None

    def write(self, text: str):
        if self.proc.stdin is not None:
            logger.info(f"IN: '{text}'")
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
