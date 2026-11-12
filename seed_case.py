"""S03 contract: assert normalize_name(' ') is None."""

def normalize_name(v): return v.strip() or None
