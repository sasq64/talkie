import unittest

from talkie.draw import PixelCanvas


class TestDraw(unittest.TestCase):
    def test_draw_line_diagonal(self):
        w = h = 5
        canvas = PixelCanvas(w, h)

        canvas.draw_line(0, 0, 4, 4, 1)

        expected_on = {(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)}
        for y in range(h):
            for x in range(w):
                idx = y * w + x
                if (x, y) in expected_on:
                    self.assertEqual(canvas.array[idx], 1)
                else:
                    self.assertEqual(canvas.array[idx], 0)

    def test_flood_fill_enclosed_area(self):
        w = h = 5
        canvas = PixelCanvas(w, h)

        # Create a 3x3 box border with color 2 from (1,1) to (3,3)
        canvas.draw_line(1, 1, 3, 1, 2)  # top
        canvas.draw_line(1, 3, 3, 3, 2)  # bottom
        canvas.draw_line(1, 1, 1, 3, 2)  # left
        canvas.draw_line(3, 1, 3, 3, 2)  # right

        # Flood fill inside the box with color 5, starting from color 0
        canvas.flood_fill(2, 2, 5, 0)

        # Verify inside is filled, border intact, outside unchanged
        def at(x, y):
            return canvas.array[y * w + x]

        # Interior
        self.assertEqual(at(2, 2), 5)

        # Border
        border_pixels = [(x, 1) for x in range(1, 4)] + \
                        [(x, 3) for x in range(1, 4)] + \
                        [(1, y) for y in range(1, 4)] + \
                        [(3, y) for y in range(1, 4)]
        for x, y in border_pixels:
            self.assertEqual(at(x, y), 2)

        # Outside still zero
        for y in range(h):
            for x in range(w):
                if (x, y) == (2, 2) or (x, y) in border_pixels:
                    continue
                self.assertEqual(at(x, y), 0)


if __name__ == "__main__":
    unittest.main()
