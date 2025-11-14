from typing import TypeVar
import pixpy as pix
from array import array


def wrap_lines(lines: list[str], max_len: int, break_chars: str = " ") -> list[str]:
    result: list[str] = []
    for line in lines:
        start = 0
        while start <= len(line):
            # Try to find a break point
            end = min(start + max_len, len(line))
            if end == len(line):
                result.append(line[start:end])
                break
            # Scan backwards for break char
            break_pos = -1
            for i in range(end - 1, start - 1, -1):
                if line[i] in break_chars:
                    break_pos = i + 1  # include the break character
                    break
            if break_pos == -1 or break_pos == start:
                # no break char found, or stuck — force break
                break_pos = end
            result.append(line[start:break_pos].rstrip())
            start = break_pos
    if len(result) == 0:
        result = [""]
    return result


def wrap_text(text: str, font: pix.Font, size: int, width: float) -> list[str]:
    lines: list[str] = []

    text = text.strip()
    start = 0
    length = len(text)

    # print(f"len {length}")
    while start < length:
        # Binary search for max character count fitting in width
        low = 1
        high = length - start
        best = 1

        if font.text_size(text[start:], size).x <= width:
            lines.append(text[start:])
            break

        while low <= high:
            mid = (low + high) // 2
            candidate = text[start : start + mid]
            if font.text_size(candidate, size).x <= width:
                best = mid
                low = mid + 1
            else:
                high = mid - 1

        # print(f"break '{text}' at {high} = {text[start:start+high]}")

        # Try to break at a space for better word boundaries
        line_end = start + best
        space_pos = text.rfind(" ", start, line_end)
        if space_pos != -1 and space_pos > start:
            line_end = space_pos

        line = text[start:line_end].rstrip()
        lines.append(line)

        # Move start index past the line (and skip leading spaces)
        start = line_end
        while start < length and text[start] == " ":
            start += 1

    # /"lenprint(f"{lines}")
    return lines


T = TypeVar("T", bound=int)


def wrap_array(
    lines: list[array[int]], max_len: int, break_chars: array[int]
) -> list[array[int]]:
    """Wrap arrays just like wrap_lines, but using array('w') directly."""
    result: list[array[int]] = []
    mask: int = 0xFFFFFFFF
    for line in lines:
        start = 0
        while start <= len(line):
            # Try to find a break point
            end = min(start + max_len, len(line))
            if end == len(line):
                result.append(line[start:end])
                break
            # Scan backwards for break char
            break_pos = -1
            for i in range(end - 1, start - 1, -1):
                if (line[i] & mask) in break_chars:
                    break_pos = i + 1  # include the break character
                    break
            if break_pos == -1 or break_pos == start:
                # no break char found, or stuck — force break
                break_pos = end

            # Get the slice and remove trailing spaces
            slice_arr = line[start:break_pos]
            while len(slice_arr) > 0 and (slice_arr[-1] & mask) in break_chars:
                slice_arr.pop()
            result.append(slice_arr)

            start = break_pos
    if len(result) == 0:
        result.append(lines[0][0:0])
    return result
