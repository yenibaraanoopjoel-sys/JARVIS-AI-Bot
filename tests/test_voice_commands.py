from jarvis.voice.commands import (
    current_date_response,
    current_time_response,
    parse_local_command,
)


def test_app_launch_commands_are_normalized():
    parsed = parse_local_command("JARVIS, open calculator")
    assert parsed is not None
    assert parsed.argument == "calculator"
    assert parse_local_command("please open the text editor") is None
    parsed = parse_local_command("Hey JARVIS launch PowerShell")
    assert parsed is not None
    assert parsed.action == "open_application"
    assert parsed.argument == "powershell"


def test_time_and_date_commands_are_deterministic():
    time_command = parse_local_command("what time is it")
    date_command = parse_local_command("JARVIS, what is today's date")
    assert time_command is not None and time_command.action == "current_time"
    assert date_command is not None and date_command.action == "current_date"
    assert "It is " in current_time_response()
    assert "Today is " in current_date_response()


def test_face_identification_requires_an_explicit_command():
    parsed = parse_local_command("JARVIS, who is in front of me")
    assert parsed is not None
    assert parsed.action == "identify_face"
    assert parse_local_command("tell me a funny story") is None
