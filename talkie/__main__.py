"""Main entry point for running talkie as a module."""
import logging
import sys
from typing import override

from .talkie import main

# logging.basicConfig(filename='talkie.log', encoding='utf-8', level=logging.DEBUG)

class IndentMultiline(logging.Formatter):
    @override
    def format(self, record : logging.LogRecord):
        s = super().format(record)
        head, *rest = s.splitlines()
        if rest:
            rest = ["    " + line for line in rest]
            return "\n".join([head, *rest])
        return s

fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
#handler = logging.StreamHandler(sys.stdout)
handler = logging.FileHandler("talkie.log", encoding="utf-8")
handler.setFormatter(IndentMultiline(fmt))
#handler.setLevel(logging.DEBUG)
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)



if __name__ == "__main__":
    main()
