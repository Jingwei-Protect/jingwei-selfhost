"""C2PA verify summary helpers."""

from core.c2pa_verify import summarize_c2pa_raw


def test_summarize_empty_when_no_manifest() -> None:
    out = summarize_c2pa_raw({})
    assert out["found"] is False
    assert out["available"] is True


def test_summarize_finds_generator() -> None:
    raw = {
        "manifests": [{
            "claim_generator": "Adobe Photoshop",
            "assertions": [{"label": "c2pa.actions", "data": {"actions": [{"action": "c2pa.created"}]}}],
        }],
    }
    out = summarize_c2pa_raw(raw)
    assert out["found"] is True
    assert out["claim_generator"] == "Adobe Photoshop"
    assert "c2pa.created" in out["actions"]

def test_summarize_sdk_missing() -> None:
    out = summarize_c2pa_raw(None)
    assert out["found"] is False
    assert out["available"] is False
