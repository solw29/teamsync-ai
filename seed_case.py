"""S02 contract: assert parse_age(-1) is None."""

def parse_age(v): return int(v) if str(v).isdigit() else None
