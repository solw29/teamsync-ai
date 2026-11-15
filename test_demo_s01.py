"""Intentional red test for the S01 bug PR; not a regression on main."""

import pytest

from demo_s01 import safe_divide


@pytest.mark.parametrize("a,b,expected", [(6, 2, 3), (1, 0, None)])
def test_safe_divide_contract(a, b, expected):
    assert safe_divide(a, b) == expected
