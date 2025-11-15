from __future__ import annotations

from dataclasses import dataclass

from slidequest.views.master.ai_reference_store import ReferenceImportStats


@dataclass(slots=True)
class ReferenceImportPayload:
    attempted: int
    added: int
    failed: int
    failure_samples: list[dict[str, str]]
    duration_ms: int

    def to_dict(self) -> dict[str, int | list[dict[str, str]]]:
        return {
            "attempted": self.attempted,
            "added": self.added,
            "failed": self.failed,
            "failure_samples": self.failure_samples,
            "duration_ms": self.duration_ms,
        }


def build_reference_import_payload(stats: ReferenceImportStats, duration_seconds: float) -> dict[str, object]:
    failure_samples = [
        {"path": path, "reason": reason}
        for path, reason in stats.failed
    ][:5]
    payload = ReferenceImportPayload(
        attempted=stats.attempted,
        added=stats.added,
        failed=len(stats.failed),
        failure_samples=failure_samples,
        duration_ms=int(max(duration_seconds, 0.0) * 1000),
    )
    return payload.to_dict()
