"""Automated test for hello.py."""

from hello import (
    cloud_agent_test,
    cloud_agent_test_2,
    goodbye,
    gpt_bridge_test,
    hello,
    mcp_bridge_test,
    security_test,
    trigger_bridge_test,
)


def test_hello() -> None:
    assert hello() == "hello from cloud execution golden test"


def test_goodbye() -> None:
    assert goodbye() == "goodbye from cloud execution golden test"


def test_cloud_agent_test() -> None:
    assert cloud_agent_test() == "executed inside github actions"


def test_cloud_agent_test_2() -> None:
    assert cloud_agent_test_2() == "second cloud run"


def test_trigger_bridge_test() -> None:
    assert trigger_bridge_test() == "triggered from github issue"


def test_security_test() -> None:
    assert security_test() == "security gate ok"


def test_gpt_bridge_test() -> None:
    assert gpt_bridge_test() == "gpt bridge ok"


def test_mcp_bridge_test() -> None:
    assert mcp_bridge_test() == "mcp bridge ok"
