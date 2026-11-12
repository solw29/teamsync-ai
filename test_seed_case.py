from seed_case import normalize_name

def test_contract():
    assert normalize_name(' ') is None
