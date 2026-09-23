"""Minimal module for the cloud execution golden test."""


def hello() -> str:
    """Return a greeting."""
    return "hello from cloud execution golden test"


def goodbye() -> str:
    """Return a farewell."""
    return "goodbye from cloud execution golden test"


def cloud_agent_test() -> str:
    """Return the cloud agent execution marker."""
    return "executed inside github actions"


def cloud_agent_test_2() -> str:
    """Return the second cloud agent execution marker."""
    return "second cloud run"


def trigger_bridge_test() -> str:
    """Return the bridge test marker."""
    return "triggered from github issue"


def security_test() -> str:
    """Return the security gate marker."""
    return "security gate ok"
