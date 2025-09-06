import re


def parse_text(text: str, patterns: dict[str, str]) -> dict[str, str]:
    """Parse a description by matching named regex patterns and removing matches from text.

    Args:
        text: The input text to parse
        patterns: Dict mapping names to regex patterns

    Returns:
        Dict with 'text' key containing remaining text and other keys for named matches
    """
    result: dict[str, str] = {}
    remaining_text = text

    for name, pattern in patterns.items():
        # Find all matches first
        matches = list(re.finditer(pattern, remaining_text, re.MULTILINE))
        if matches:
            # Store the first match for the result
            result[name] = matches[0].group(0)
            # Remove all occurrences by iterating through them in reverse order
            # (to avoid index shifting issues)
            for match in reversed(matches):
                match_text = match.group(0)
                # Include trailing newline if it exists to avoid double newlines
                start, end = match.start(), match.end()
                if end < len(remaining_text) and remaining_text[end] == "\n":
                    match_text += "\n"
                remaining_text = (
                    remaining_text[:start] + remaining_text[start + len(match_text) :]
                )
            remaining_text = remaining_text.strip()
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
            "copyright": r"^Copyright (.*)$",
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


def partition_text(text: str, max_len: int) -> list[str]:
    """Split text into chunks of maximum length, using intelligent splitting.

    Args:
        text: The input text to partition
        max_len: Maximum length for each chunk

    Returns:
        List of text chunks, each <= max_len characters
    """
    if not text or max_len <= 0:
        return [] if not text else [text]

    if len(text) <= max_len:
        return [text]

    # First, split on empty lines (double linefeeds)
    paragraphs = re.split(r"\n\s*\n", text)

    result: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_len:
            result.append(paragraph)
        else:
            # Split paragraph further
            result.extend(_split_paragraph(paragraph, max_len))

    return result


def _split_paragraph(text: str, max_len: int) -> list[str]:
    """Split a paragraph that's too long using sentence boundaries."""
    if len(text) <= max_len:
        return [text]

    # Try splitting on sentence ending + linefeed first
    sentences = re.split(r"([.!?]\n)", text)
    if len(sentences) > 1:
        # Rejoin split parts with their delimiters
        rejoined: list[str] = []
        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                rejoined.append(sentences[i] + sentences[i + 1])
            else:
                rejoined.append(sentences[i])
        sentences = rejoined
    else:
        sentences = [text]

    result: list[str] = []
    current_chunk = ""

    for sentence in sentences:
        if not sentence.strip():
            continue

        if len(current_chunk) + len(sentence) <= max_len:
            current_chunk += sentence
        else:
            if current_chunk:
                result.append(current_chunk.strip())
                current_chunk = ""

            if len(sentence) <= max_len:
                current_chunk = sentence
            else:
                # Single sentence is too long, split on any sentence end
                result.extend(_split_by_sentence_end(sentence, max_len))

    if current_chunk:
        result.append(current_chunk.strip())

    return result


def _split_by_sentence_end(text: str, max_len: int) -> list[str]:
    """Split text on any sentence ending punctuation."""
    if len(text) <= max_len:
        return [text]

    # Split on sentence endings anywhere
    sentences = re.split(r"([.!?])", text)
    # Rejoin split parts with their delimiters
    sentences = ["".join(sentences[i : i + 2]) for i in range(0, len(sentences), 2)]

    result: list[str] = []
    current_chunk = ""

    for sentence in sentences:
        if not sentence.strip():
            continue

        if len(current_chunk) + len(sentence) <= max_len:
            current_chunk += sentence
        else:
            if current_chunk:
                result.append(current_chunk.strip())
                current_chunk = sentence
            else:
                # If single sentence is still too long, split arbitrarily
                while len(sentence) > max_len:
                    result.append(sentence[:max_len])
                    sentence = sentence[max_len:]
                if sentence:
                    current_chunk = sentence

    if current_chunk:
        result.append(current_chunk.strip())

    return result
