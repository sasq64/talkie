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
        self.array : Final = array.array('B', [0] * w * h)
        self.width : int = w
        self.height : int = h
        self.target_color : int = -1

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def _index(self, x: int, y: int) -> int:
        return y * self.width + x

    def clear(self, color: int):
        for i in range(len(self.array)):
            self.array[i] = color

    def flood_fill(self, x: int, y: int, col: int) -> None:
        """Flood-fill the region containing (x, y) with color `col`.

        - Uses 4-connectivity (up, down, left, right).
        - Does nothing if (x, y) is out of bounds or if the starting pixel
          already has color `col`.
        """

        if not self._in_bounds(x, y):
            return

        start_idx = self._index(x, y)
        target = self.array[start_idx]
        if target == col:
            return
        if self.target_color != -1 and target != self.target_color:
            return

        stack: list[tuple[int, int]] = [(x, y)]
        while stack:
            cx, cy = stack.pop()
            if not self._in_bounds(cx, cy):
                continue
            idx = self._index(cx, cy)
            if self.array[idx] != target:
                continue

            # Fill current pixel
            self.array[idx] = col

            # Add 4-connected neighbors
            stack.append((cx + 1, cy))
            stack.append((cx - 1, cy))
            stack.append((cx, cy + 1))
            stack.append((cx, cy - 1))

    def draw_line(self, x0: int, y0: int, x1: int, y1: int, col: int) -> None:
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
                if self.target_color == -1 or self.target_color == current:
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
