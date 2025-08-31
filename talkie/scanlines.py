from math import cos, pi


def make_scanline_texture(
    height: int,
    pitch: float = 2.5,
    dark: float = 0.55,
    soft: bool = True,
    gamma: float = 2.0,
    offset: float = 0.0,
) -> list[float]:
    """
    Generate a 1px-wide scanline texture for multiply blending.

    Args:
        height: Number of rows (same as your target surface height).
        pitch: Distance in pixels between scanline centers (e.g. 2–3 looks nice).
        dark: Minimum intensity at the darkest part of a line (0..1).
        soft: If True, use a cosine falloff for softer lines; else hard 1px lines.
        gamma: Curve for the soft falloff (higher = tighter dark core).
        offset: Vertical phase offset in pixels (can animate by changing this).

    Returns:
        List[float] of length `height`, values in [0.0, 1.0].
    """
    if pitch <= 0:
        raise ValueError("pitch must be > 0")
    if not (0.0 <= dark <= 1.0):
        raise ValueError("dark must be in [0, 1]")

    out: list[float] = []
    for y in range(height):
        if soft:
            # Phase 0..1, where 0 is line center
            phase = ((y + offset) % pitch) / pitch
            t = 0.5 * (1.0 + cos(2.0 * pi * phase))  # 1 at center, 0 halfway
            v = dark + (1.0 - dark) * (t**gamma)  # raise floor to `dark`
        else:
            v = dark if ((y + offset) % pitch) < 1.0 else 1.0
        out.append(v)
    return out
