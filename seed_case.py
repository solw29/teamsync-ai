"""S04 contract: assert discount(10,2) is None."""

def discount(p,r): return p*(1-r) if p >= 0 and 0 <= r <= 1 else None
