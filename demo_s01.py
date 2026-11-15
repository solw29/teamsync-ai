"""S01 demonstration contract: a zero divisor must return None, not raise."""


def safe_divide(a: float, b: float) -> float | None:
    """Return None for b == 0, otherwise return a / b."""
    return a / b
