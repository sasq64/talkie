import time
import math

import pytest

from talkie.draw import PixelCanvas


def _time_it(fn, iterations: int = 1) -> float:
    """Return total seconds for running fn() `iterations` times."""
    # Light warmup to stabilize caches/branch prediction
    for _ in range(min(3, iterations)):
        fn()
    start = time.perf_counter()
    for _ in range(iterations):
        fn()
    end = time.perf_counter()
    return end - start


@pytest.mark.slow
def test_bench_clear():
    # 512x512 ~ 262k pixels
    w = h = 512
    canvas = PixelCanvas(w, h)

    # Measure clearing with changing colors to avoid fast-paths
    iterations = 50

    def run():
        # Change the color each time to avoid constant-folded effects
        # (still writes every pixel)
        nonlocal color
        canvas.clear(color)
        color = (color + 17) & 0xFF

    color = 0
    total = _time_it(run, iterations)
    per_op_us = (total / iterations) * 1e6
    print(f"clear() total: {total:.4f}s, avg: {per_op_us:.2f} µs/op over {iterations} iters")


@pytest.mark.slow
def test_bench_draw_line():
    # Draw a fan of lines from each corner across the canvas
    w = h = 512
    canvas = PixelCanvas(w, h)

    # Precompute a set of endpoints to cover various slopes
    step = 16
    endpoints = [(x, 0) for x in range(0, w, step)] + [
        (w - 1, y) for y in range(0, h, step)
    ]

    def run_once():
        col = 1
        # Top-left fan
        for x, y in endpoints:
            canvas.draw_line(0, 0, x, y, col)
            col = (col + 1) & 0xFF
        # Top-right fan
        for x, y in endpoints:
            canvas.draw_line(w - 1, 0, x, y, col)
            col = (col + 1) & 0xFF
        # Bottom-left fan
        for x, y in endpoints:
            canvas.draw_line(0, h - 1, x, y, col)
            col = (col + 1) & 0xFF
        # Bottom-right fan
        for x, y in endpoints:
            canvas.draw_line(w - 1, h - 1, x, y, col)

    iterations = 10
    total = _time_it(run_once, iterations)
    ops = iterations * 4 * len(endpoints)
    per_line_us = (total / ops) * 1e6
    print(
        f"draw_line() total: {total:.4f}s, lines: {ops}, avg: {per_line_us:.2f} µs/line"
    )


@pytest.mark.slow
def test_bench_flood_fill():
    # Create a grid of cells separated by 1px walls, then fill distinct cells.
    w = h = 256
    canvas = PixelCanvas(w, h)

    # Draw a simple grid (every 16 pixels) using color 2 as walls
    wall = 2
    spacing = 16
    for x in range(0, w):
        if x % spacing == 0:
            canvas.draw_line(x, 0, x, h - 1, wall)
    for y in range(0, h):
        if y % spacing == 0:
            canvas.draw_line(0, y, w - 1, y, wall)

    # Choose a set of seed points inside different cells
    seeds = []
    for cy in range(spacing // 2, h, spacing):
        for cx in range(spacing // 2, w, spacing):
            seeds.append((cx, cy))
    # Sample a subset to keep runtime modest
    seeds = seeds[0:64]

    def run_once():
        # Alternate fill colors so we don't immediately exit due to same-color
        # early return in flood_fill
        nonlocal col
        for (sx, sy) in seeds:
            canvas.flood_fill(sx, sy, col)
            col = 1 if col == 3 else 3

    col = 1
    iterations = 5
    total = _time_it(run_once, iterations)
    ops = iterations * len(seeds)
    per_fill_us = (total / ops) * 1e6
    print(
        f"flood_fill() total: {total:.4f}s, fills: {ops}, avg: {per_fill_us:.2f} µs/fill"
    )

