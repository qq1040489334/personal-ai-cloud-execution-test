"""Automated test for hello.py."""

from hello import hello


def test_hello() -> None:
    assert hello() == "hello from cloud execution golden test"
