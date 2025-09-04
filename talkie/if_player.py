import contextlib
import queue
import re
import subprocess
import threading
import time
from dataclasses import dataclass
from importlib import resources
from io import BufferedReader
from logging import getLogger
from pathlib import Path
from typing import Final

from talkie.image_drawer import ImageDrawer

from .text_utils import parse_adventure_description, trim_lines, unwrap_text

logger = getLogger(__name__)


@dataclass
class IFOutput:
    text: str
    all_text: str
    image: Path | None


class IFPlayer:
    def __init__(
        self, image_drawer: ImageDrawer, file_name: Path, gfx_path: Path | None = None
    ):
        """
        Start an interactive fiction game in a subprocess
        """

        zcode = re.compile(r"\.z(ode|[123456789])$")
        l9 = re.compile(r"\.l9$")
        data = resources.files("talkie.data")
        self.image_drawer = image_drawer
        self.key_mode: bool = False

        if zcode.search(file_name.name):
            args = ["dfrotz", "-m", "-w", "1000", file_name.as_posix()]
        elif l9.search(file_name.name):
            if gfx_path:
                gfx_str = gfx_path.as_posix()
                if gfx_path.is_dir():
                    gfx_str += "/"
                args = [str(data / "l9"), file_name.as_posix(), gfx_str]
            else:
                args = [str(data / "l9"), file_name.as_posix()]
        else:
            raise RuntimeError("Unknown format")
        print(args)

        self.proc: Final = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.output_queue: queue.Queue[bytes] = queue.Queue()
        self.transcript: list[tuple[str, str]] = []
        self.text_output: str = ""
        self.last_result: float = 0

        # TODO: Handle stderr, and handle split command in stdout
        def _read_output(fout: BufferedReader):
            while True:
                if fout:
                    data: bytes = fout.read1(16384)  # type: ignore
                    if not data:
                        break
                    self.output_queue.put(data)

        self.output_thread: Final = threading.Thread(
            target=_read_output, args=(self.proc.stdout,), daemon=True
        )
        self.output_thread.start()

        self._closed: bool = False

    def read(self) -> IFOutput | None:
        """
        Read stdout from running interpreter. Returns a dict containing
        both the raw text and context aware parsing (like stripping the
            status bar from frotz etc).
        """
        try:
            raw_text = self.output_queue.get_nowait()
            result = raw_text.decode()
            self.text_output += result
            self.last_result = time.time()
        except queue.Empty:
            pass
        return self._handle_output()

    def _handle_output(self) -> IFOutput | None:
        if not self.text_output or time.time() - self.last_result < 0.25:
            return None

        # We have a full set of text
        meta = re.compile(r"#\[(.*?)\]\n?")
        text = trim_lines(self.text_output)
        found_gfx = False
        for line in text.splitlines():
            for m in re.finditer(meta, line):
                match = m.group(1)
                if match == "keymode":
                    self.key_mode = True
                elif match == "linemode":
                    self.key_mode = False
                if self.image_drawer.add_text_command(match):
                    found_gfx = True

        text = meta.sub("", text)

        text = unwrap_text(text)
        ps = text.split("\n\n")
        if len(ps) > 2:
            first = ps[0].strip()
            for px in ps[1:]:
                if px and px.splitlines()[0].strip() == first:
                    logger.debug(f"Dropping first line '{first}'")
                    _ = ps.pop(0)
                    break
            text = "\n\n".join(ps)
        fields = parse_adventure_description(text)
        logger.debug(f"Parsed: '{text}' into:\n{fields}")
        self.transcript.append((":", str(fields["text"])))
        fields["full_text"] = self.text_output
        image = self.image_drawer.get_image() if found_gfx else None
        output = IFOutput(fields["text"], self.text_output, image)
        self.text_output = ""
        return output

    def get_image(self) -> Path:
        return self.image_drawer.get_image()

    def write(self, text: str):
        """Write text line to stdin of running interpreter."""

        if self.proc.stdin is not None:
            print(f"IN:'{text}'")
            logger.info(f"IN: '{text}'")
            _ = self.proc.stdin.write(text.encode())
            self.transcript.append((">", text))
            self.proc.stdin.flush()

    def get_transcript(self) -> str:
        """Get the transcript of the game so far."""

        lines: list[str] = []
        for c, line in self.transcript:
            if c == ">":
                lines.append("\n>" + line)
            else:
                lines.append(line)
        return "\n".join(lines)

    def _cleanup(self):
        """Internal cleanup method to terminate subprocess and thread."""
        if self._closed:
            return

        self._closed = True
        # Terminate the subprocess
        if hasattr(self, "proc") and self.proc:
            try:
                # Close stdin to signal the process to exit gracefully
                if self.proc.stdin:
                    self.proc.stdin.close()

                # Wait briefly for graceful shutdown
                try:
                    _ = self.proc.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't exit gracefully
                    logger.warning("Subprocess didn't exit gracefully, terminating...")
                    self.proc.terminate()
                    try:
                        _ = self.proc.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        logger.warning("Subprocess didn't respond to TERM, killing...")
                        self.proc.kill()
                        _ = self.proc.wait()

                logger.info(
                    f"IFPlayer subprocess terminated with return code: {self.proc.returncode}"
                )
            except Exception as e:
                logger.error(f"Error terminating subprocess: {e}")

    def close(self):
        """Explicitly close the IFPlayer and cleanup resources."""
        self._cleanup()

    def __del__(self):
        """Ensure cleanup during garbage collection."""
        try:
            self._cleanup()
        except Exception:
            # Ignore errors during garbage collection
            _ = contextlib.suppress(Exception)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object | None):
        """Context manager exit with cleanup."""
        self.close()
        return False
