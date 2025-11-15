from __future__ import annotations

from slidequest.views.master.ai_reference_store import ReferenceImportStats
from slidequest.views.master.ai_telemetry import build_reference_import_payload


def test_build_reference_import_payload_truncates_failures() -> None:
    stats = ReferenceImportStats(attempted=5, added=2)
    stats.failed = [(f"file{i}.png", "error") for i in range(6)]
    payload = build_reference_import_payload(stats, duration_seconds=1.5)
    assert payload["attempted"] == 5
    assert payload["added"] == 2
    assert payload["failed"] == 6
    assert payload["duration_ms"] == 1500
    samples = payload["failure_samples"]
    assert len(samples) == 5
    assert samples[0]["path"] == "file0.png"
