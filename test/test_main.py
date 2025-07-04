"""Unit tests for main.py functions related to PagerDuty and Slack integration."""

from unittest.mock import MagicMock, patch

import main


@patch("main.pagerduty_client")
def test_get_on_call_schedule_name(mock_pd_client):
    """Test fetching the on-call schedule name from PagerDuty."""
    mock_pd_client.get.return_value.ok = True
    mock_pd_client.get.return_value.json.return_value = {
        "schedule": {"name": "Test Schedule"}
    }
    assert main.get_on_call_schedule_name() == "Test Schedule"


@patch("main.pagerduty_client")
def test_get_on_call_user(mock_pd_client):
    """Test fetching the on-call user's name and email from PagerDuty."""
    mock_pd_client.get.side_effect = [
        MagicMock(
            ok=True,
            json=lambda: {
                "users": [{"name": "Alice", "id": "U1", "email": "alice@example.com"}]
            },
        ),
        MagicMock(
            ok=True,
            json=lambda: {
                "user": {
                    "contact_methods": [
                        {"label": "Default", "address": "alice@work.com"}
                    ]
                }
            },
        ),
    ]
    name, email = main.get_on_call_user()
    assert name == "Alice"
    assert email == "alice@work.com"


@patch("main.slack_client")
@patch("main.get_on_call_user")
def test_get_slack_user_id(mock_get_user, mock_slack_client):
    """Test fetching the Slack user ID for the on-call user."""
    mock_get_user.return_value = ("Alice", "alice@work.com")
    mock_slack_client.users_lookupByEmail.return_value = {"user": {"id": "SLACK123"}}
    assert main.get_slack_user_id() == "SLACK123"


@patch("main.slack_client")
@patch("main.get_slack_user_id")
@patch("main.get_on_call_user")
@patch("main.get_on_call_schedule_name")
def test_main(mock_sched, mock_user, mock_slack_id, mock_slack_client):
    """Test the main function to ensure it posts the correct message to Slack."""
    mock_sched.return_value = "Test Schedule"
    mock_user.return_value = ("Alice", "alice@work.com")
    mock_slack_id.return_value = "SLACK123"
    main.main()
    mock_slack_client.chat_postMessage.assert_called_with(
        channel=main.slack_channel,
        text="<@SLACK123> is on support for Test Schedule",
    )
