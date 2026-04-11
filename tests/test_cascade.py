"""Tests for retryctl.cascade."""
import pytest
from retryctl.cascade import CascadeConfig, CascadeStep, should_run_step, run_cascade


# ---------------------------------------------------------------------------
# CascadeConfig.from_dict
# ---------------------------------------------------------------------------

def test_from_dict_defaults():
    cfg = CascadeConfig.from_dict({})
    assert cfg.enabled is False
    assert cfg.steps == []
    assert cfg.stop_on_success is True


def test_from_dict_full():
    raw = {
        "enabled": True,
        "stop_on_success": False,
        "steps": [
            {"command": "notify.sh", "on": "failure"},
            {"command": "cleanup.sh", "on": "always"},
        ],
    }
    cfg = CascadeConfig.from_dict(raw)
    assert cfg.enabled is True
    assert cfg.stop_on_success is False
    assert len(cfg.steps) == 2
    assert cfg.steps[0].command == "notify.sh"
    assert cfg.steps[1].on == "always"


def test_from_dict_auto_enables_when_steps_present():
    raw = {"steps": [{"command": "echo hi"}]}
    cfg = CascadeConfig.from_dict(raw)
    assert cfg.enabled is True


def test_from_dict_invalid_type_raises():
    with pytest.raises(TypeError):
        CascadeConfig.from_dict("not a dict")  # type: ignore


def test_from_dict_steps_not_list_raises():
    with pytest.raises(TypeError):
        CascadeConfig.from_dict({"steps": "bad"})


def test_from_dict_step_missing_command_raises():
    with pytest.raises(ValueError):
        CascadeConfig.from_dict({"steps": [{"on": "failure"}]})


def test_from_dict_step_invalid_on_raises():
    with pytest.raises(ValueError):
        CascadeConfig.from_dict({"steps": [{"command": "x", "on": "maybe"}]})


# ---------------------------------------------------------------------------
# should_run_step
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("on,last_ok,expected", [
    ("failure", False, True),
    ("failure", True,  False),
    ("success", True,  True),
    ("success", False, False),
    ("always",  True,  True),
    ("always",  False, True),
])
def test_should_run_step(on, last_ok, expected):
    step = CascadeStep(command="cmd", on=on)
    assert should_run_step(step, last_ok) == expected


# ---------------------------------------------------------------------------
# run_cascade
# ---------------------------------------------------------------------------

def test_run_cascade_disabled_returns_empty():
    cfg = CascadeConfig(enabled=False, steps=[CascadeStep(command="x")])
    assert run_cascade(cfg, last_succeeded=False) == []


def test_run_cascade_selects_on_failure():
    cfg = CascadeConfig(
        enabled=True,
        steps=[
            CascadeStep(command="alert.sh", on="failure"),
            CascadeStep(command="celebrate.sh", on="success"),
        ],
    )
    result = run_cascade(cfg, last_succeeded=False)
    assert result == ["alert.sh"]


def test_run_cascade_always_step_always_included():
    cfg = CascadeConfig(
        enabled=True,
        steps=[CascadeStep(command="log.sh", on="always")],
    )
    assert run_cascade(cfg, last_succeeded=True) == ["log.sh"]
    assert run_cascade(cfg, last_succeeded=False) == ["log.sh"]


def test_run_cascade_stop_on_success_chains_correctly():
    cfg = CascadeConfig(
        enabled=True,
        stop_on_success=True,
        steps=[
            CascadeStep(command="fix.sh", on="failure"),
            CascadeStep(command="still_broken.sh", on="failure"),
        ],
    )
    # first step runs (failure), then stop_on_success flips state -> second skipped
    result = run_cascade(cfg, last_succeeded=False)
    assert result == ["fix.sh"]


def test_run_cascade_no_stop_on_success_runs_all_matching():
    cfg = CascadeConfig(
        enabled=True,
        stop_on_success=False,
        steps=[
            CascadeStep(command="a.sh", on="failure"),
            CascadeStep(command="b.sh", on="failure"),
        ],
    )
    result = run_cascade(cfg, last_succeeded=False)
    assert result == ["a.sh", "b.sh"]
