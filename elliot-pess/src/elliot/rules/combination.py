"""Double three W-X-Y. X must not pass the origin of W."""

from __future__ import annotations

from elliot.models import Direction


def x_exceeds_w_origin(origin: float, x_end: float, w_direction: Direction) -> bool:
    """A bearish W starts at a high; an upward X that reaches that high breaks the link."""
    if w_direction == "bearish":
        return x_end >= origin
    return x_end <= origin
