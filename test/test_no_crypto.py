import time
from src.logging_config import logger

import pytest

from src.mavlink_proxy.command_intake import CommandIntake


class FakeMsg:
    """Minimal stand-in for pymavlink messages used in unit tests."""

    def __init__(self, msg_type: str, msg_id: int, data: dict):
        self._msg_type = msg_type
        self._msg_id = msg_id
        self._data = data

    def get_type(self) -> str:
        return self._msg_type

    def get_msgId(self) -> int:
        return self._msg_id

    def to_dict(self) -> dict:
        return dict(self._data)


@pytest.fixture()
def intake():
    # Bypass CommandIntake.__init__ to avoid opening a real MAVLink socket.
    return CommandIntake.__new__(CommandIntake)


def test_non_command_messages_are_ignored(intake):
    logger.info("Testing non-command message filtering")
    msg = FakeMsg("HEARTBEAT", 10, {})
    result = intake.parse_command(msg)
    assert result is None
    logger.info("Non-command message correctly ignored")


def test_command_long_classification_and_params(intake):
    logger.info("Testing COMMAND_LONG classification")
    msg = FakeMsg(
        "COMMAND_LONG",
        42,
        {"command": 20, "target_system": 255, "target_component": 1},
    )

    cmd = intake.parse_command(msg)

    assert cmd is not None
    assert cmd.command_type == "RETURN"  # COMMAND_LONG with MAV_CMD_NAV_RETURN_TO_LAUNCH
    assert cmd.source == "gcs"
    assert cmd.params["command"] == 20
    assert cmd.sys_id == 255
    assert cmd.comp_id == 1
    logger.info("COMMAND_LONG correctly classified and parsed")


def test_navigation_command_is_parsed(intake):
    logger.info("Testing navigation command parsing")
    msg = FakeMsg(
        "SET_POSITION_TARGET_LOCAL_NED",
        11,
        {
            "x": 1.0,
            "y": 2.0,
            "z": -3.0,
            "vx": 0.1,
            "vy": 0.2,
            "vz": -0.3,
            "type_mask": 0,
            "target_system": 2,
            "target_component": 1,
        },
    )

    cmd = intake.parse_command(msg)

    assert cmd is not None
    assert cmd.command_type == "NAVIGATION"
    assert cmd.params["x"] == 1.0
    assert cmd.params["vz"] == -0.3
    assert cmd.source == "companion"
    logger.info("Navigation command correctly parsed")


def test_parse_latency_under_budget(intake):
    logger.info("Testing command parsing latency")
    messages = [
        FakeMsg(
            "COMMAND_LONG",
            i,
            {"command": 176, "target_system": 2, "target_component": 1},
        )
        for i in range(50)
    ]

    start = time.perf_counter()
    for msg in messages:
        intake.parse_command(msg)
    avg_duration = (time.perf_counter() - start) / len(messages)

    assert avg_duration < 0.01, f"Command parsing avg latency {avg_duration:.4f}s exceeded budget"
    logger.info(f"Latency test passed: {avg_duration:.4f}s average")
