from demo_s01 import safe_divide

def test_contract():
    assert safe_divide(1,0) is None
