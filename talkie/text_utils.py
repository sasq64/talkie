import re


def parse_text(text: str, patterns: dict[str, str]) -> dict[str, str]:
    """Parse a description by matching named regex patterns and removing matches from text.

    Args:
        text: The input text to parse
        patterns: Dict mapping names to regex patterns

    Returns:
        Dict with 'text' key containing remaining text and other keys for named matches
    """
    result : dict[str, str] = {}
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
            "title": r"^(.*)\ {5,}(.*)$",
            "title2": r"^\ {5,}(.*)\w$",
            "header": r"^Using normal.*\nLoading.*$",
            "trademark": r"^.*trademark.*nfocom.*$",
            "release": r"^Release.*Serial.*$",
            "warning": r"^Warning:.*$",
            "prompt": r"\n+>",
            "copyright": r"^Copyright (.*)",
        },
    )


def unwrap_text(text: str, colum: int = 200) -> str:
    """
    Try to unwrap wrapped text. Assumes any line that is longer than 'column' and does not end in punctuation should be joined with the next line.
    """

    pattern = re.compile(r"[.?!>:]$")
    new_lines: list[str] = []
    last_line: str = ""
    for line in text.splitlines():
        if len(line) > colum and not pattern.search(line):
            last_line = last_line + " " + line if last_line != "" else line
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
