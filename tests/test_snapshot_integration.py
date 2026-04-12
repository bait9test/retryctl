"""Integration tests: snapshot across a simulated retry loop."""
from __future__ import annotations

from retryctl.snapshot import SnapshotConfig, SnapshotEntry
from retryctl.snapshot_middleware import on_attempt_complete


def _run_loop(tmp_path, outputs: list[str]) -> list[SnapshotEntry]:
    """Simulate a retry loop producing the given stdout strings."""
    cfg = SnapshotConfig(enabled=True, path=str(tmp_path))
    history: list[SnapshotEntry] = []
    for i, out in enumerate(outputs, start=1):
        _, history = on_attempt_complete(cfg, "test-cmd", i, out, None, history)
    return history


def test_stable_output_never_marks_changed(tmp_path):
    history = _run_loop(tmp_path, ["same", "same", "same"])
    assert all(not e.changed for e in history)


def test_first_change_detected(tmp_path):
    history = _run_loop(tmp_path, ["a", "b"])
    assert history[0].changed is False
    assert history[1].changed is True


def test_change_then_stable(tmp_path):
    history = _run_loop(tmp_path, ["a", "b", "b", "b"])
    changed_flags = [e.changed for e in history]
    assert changed_flags == [False, True, False, False]


def test_multiple_changes(tmp_path):
    history = _run_loop(tmp_path, ["x", "y", "z"])
    assert history[0].changed is False
    assert history[1].changed is True
    assert history[2].changed is True


def test_empty_output_stable(tmp_path):
    history = _run_loop(tmp_path, ["", "", ""])
    assert all(not e.changed for e in history)


def test_snapshots_persisted_to_disk(tmp_path):
    from retryctl.snapshot import load_snapshots
    cfg = SnapshotConfig(enabled=True, path=str(tmp_path))
    history: list[SnapshotEntry] = []
    for i, out in enumerate(["a", "b"], start=1):
        _, history = on_attempt_complete(cfg, "disk-test", i, out, None, history)
    loaded = load_snapshots(cfg, "disk-test")
    assert len(loaded) == 2
    assert loaded[1].changed is True
