"""Automated test for hello.py."""

from hello import cloud_agent_test, goodbye, hello


def test_hello() -> None:
    assert hello() == "hello from cloud execution golden test"


def test_goodbye() -> None:
    assert goodbye() == "goodbye from cloud execution golden test"


def test_cloud_agent_test() -> None:
    assert cloud_agent_test() == "executed inside github actions"
