"""Small, testable helpers shared by the gesture controller."""

import math


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def map_range(value, in_min, in_max, out_min, out_max):
    """Map a value between ranges; handle an empty input range safely."""
    if in_max == in_min:
        return out_min
    ratio = (float(value) - in_min) / (in_max - in_min)
    return out_min + ratio * (out_max - out_min)


def distance(point_a, point_b):
    """Distance between normalized points with x and y attributes."""
    return math.hypot(point_a.x - point_b.x, point_a.y - point_b.y)


def four_finger_pose(fingers, index=None, middle=None, ring=None, pinky=None):
    """Match [thumb, index, middle, ring, pinky]; None skips that finger."""
    wanted = (index, middle, ring, pinky)
    return all(
        expected is None or bool(fingers[position]) == expected
        for position, expected in zip((1, 2, 3, 4), wanted)
    )
