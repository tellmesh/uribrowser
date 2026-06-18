import pytest

from uribrowserdocker.handlers import _cdp_endpoint, publish_post, screenshot, submit_form


def test_screenshot_mock():
    ctx = {"params": {"session": "test"}, "config": {"browser": {"driver": "mock"}}}
    out = screenshot({}, ctx)
    assert out["mock"] is True
    assert "base64" in out


def test_publish_post_dry_run():
    ctx = {"dry_run": True, "config": {"browser": {"driver": "mock"}}, "params": {"session": "linkedin"}}
    out = publish_post({"text": "hello"}, ctx)
    assert out["dry_run"] is True
    assert out["chars"] == 5


def test_submit_form_not_screenshot():
    ctx = {"config": {"browser": {"driver": "mock"}}, "params": {"session": "test"}}
    out = submit_form({"form_id": "x", "fields": {"a": "1"}}, ctx)
    assert out["submitted"] is True
    assert "base64" not in out


def test_cdp_endpoint_precedence(monkeypatch):
    monkeypatch.delenv("URISYS_BROWSER_CDP", raising=False)
    assert _cdp_endpoint({}, {}) == "http://127.0.0.1:9222"
    assert _cdp_endpoint({"cdp_endpoint": "http://x:1"}, {}) == "http://x:1"
    assert _cdp_endpoint({"cdp_endpoint": "http://x:1"}, {"cdp": "http://y:2"}) == "http://y:2"


def test_cdp_publish_requires_allow_real(monkeypatch):
    monkeypatch.delenv("URISYS_ALLOW_REAL", raising=False)
    ctx = {"config": {"browser": {}}, "params": {"session": "linkedin"}, "allow_real": False}
    with pytest.raises(PermissionError):
        publish_post({"driver": "cdp", "text": "hi"}, ctx)
