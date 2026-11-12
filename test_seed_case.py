from seed_case import parse_age

def test_contract():
    assert parse_age(-1) is None
