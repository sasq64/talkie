"""
Bitmap drawing utilities using a simple 1D pixel buffer.

`PixelCanvas` treats `array` as a flat, mutable 1D buffer representing a
`w` by `h` bitmap in row-major order. Pixels are addressed at index
`y * w + x`.
"""

import array
from collections.abc import MutableSequence
from typing import Final


class PixelCanvas:
    """A minimal bitmap canvas backed by a 1D pixel buffer.

    - `array` is modified in-place.
    - Coordinates are 0-based, with origin at top-left.
    """

    def __init__(self, w: int, h: int) -> None:
        self.array: Final = array.array("B", [0] * w * h)
        self.width: int = w
        self.height: int = h

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def _index(self, x: int, y: int) -> int:
        return y * self.width + x

    def clear(self, color: int):
        for i in range(len(self.array)):
            self.array[i] = color

    def flood_fill(self, x: int, y: int, col: int, target_col: int) -> None:
        """Flood-fill using stack-based scanline algorithm based on os_fill from graphics.c.

        - Fills region containing (x, y) with color `col`
        - Only fills pixels that currently have color `target_col`
        - Uses stack-based scanline approach for efficiency
        """

        if col == target_col:
            return

        if not self._in_bounds(x, y):
            return

        if self.array[self._index(x, y)] != target_col:
            return

        stack: list[tuple[int, int]] = [(x, y)]

        while stack:
            cx, cy = stack.pop()

            if not self._in_bounds(cx, cy):
                continue

            if self.array[self._index(cx, cy)] != target_col:
                continue

            # Find left side, filling along the way
            left = cx
            while left >= 0 and self.array[self._index(left, cy)] == target_col:
                self.array[self._index(left, cy)] = col
                left -= 1

            left += 1

            # Find right side, filling along the way
            right = cx + 1
            while (
                right < self.width and self.array[self._index(right, cy)] == target_col
            ):
                self.array[self._index(right, cy)] = col
                right += 1

            right -= 1

            # Add spans above and below to stack
            for i in range(left, right + 1):
                if cy - 1 >= 0 and self.array[self._index(i, cy - 1)] == target_col:
                    stack.append((i, cy - 1))

                if (
                    cy + 1 < self.height
                    and self.array[self._index(i, cy + 1)] == target_col
                ):
                    stack.append((i, cy + 1))

    def draw_line(self, x0: int, y0: int, x1: int, y1: int, col: int, target_color: int = -1) -> None:
        """Draw a line from (x0, y0) to (x1, y1) using Bresenham's algorithm.

        - Writes only to in-bounds pixels.
        """

        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        err = dx + dy  # error term

        while True:
            if self._in_bounds(x0, y0):
                current = self.array[self._index(x0, y0)]
                if target_color == -1 or target_color == current:
                    self.array[self._index(x0, y0)] = col
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy
