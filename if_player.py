import subprocess
import threading
import queue
import re
import logging
from pathlib import Path


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