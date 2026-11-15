"""S01 contract: assert safe_divide(1,0) is None."""

def safe_divide(a,b): return None if b == 0 else a/b
