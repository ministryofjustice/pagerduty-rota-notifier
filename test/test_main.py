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


@patch("main.pagerduty_client")
def test_get_em_support_users(mock_pd_client):
    """Test resolving the EM primary and shadowing engineers."""
    mock_pd_client.get.return_value = MagicMock(
        ok=True,
        json=lambda: {
            "schedule": {
                "rotations": [
                    {
                        "id": "PRIMARY_ROTATION",
                        "events": [
                            {
                                "name": "Primary Monday AM - phase 1",
                            }
                        ],
                    },
                    {
                        "id": "SHADOW_ROTATION",
                        "events": [
                            {
                                "name": "Shadow member_06 - Monday AM",
                            }
                        ],
                    },
                ],
                "final_schedule": {
                    "computed_shift_assignments": [
                        {
                            "member": {
                                "type": "user_member",
                                "user_id": "PRIMARY_USER",
                            },
                            "source": {
                                "rotation_id": "PRIMARY_ROTATION",
                            },
                        },
                        {
                            "member": {
                                "type": "user_member",
                                "user_id": "SHADOW_USER",
                            },
                            "source": {
                                "rotation_id": "SHADOW_ROTATION",
                            },
                        },
                    ]
                },
            }
        },
    )

    primary_user_id, shadow_user_id = main.get_em_support_users()

    assert primary_user_id == "PRIMARY_USER"
    assert shadow_user_id == "SHADOW_USER"


@patch("main.pagerduty_client")
def test_get_em_support_users_without_shadow(mock_pd_client):
    """Test resolving EM support when nobody is shadowing."""
    mock_pd_client.get.return_value = MagicMock(
        ok=True,
        json=lambda: {
            "schedule": {
                "rotations": [
                    {
                        "id": "PRIMARY_ROTATION",
                        "events": [
                            {
                                "name": "Primary Monday AM - phase 2",
                            }
                        ],
                    }
                ],
                "final_schedule": {
                    "computed_shift_assignments": [
                        {
                            "member": {
                                "type": "user_member",
                                "user_id": "PRIMARY_USER",
                            },
                            "source": {
                                "rotation_id": "PRIMARY_ROTATION",
                            },
                        }
                    ]
                },
            }
        },
    )

    primary_user_id, shadow_user_id = main.get_em_support_users()

    assert primary_user_id == "PRIMARY_USER"
    assert shadow_user_id is None


@patch("main.slack_client")
@patch("main.pagerduty_client")
def test_get_em_slack_display_name(mock_pd_client, mock_slack_client):
    """Test resolving an EM PagerDuty user to a Slack mention."""
    mock_pd_client.get.return_value = MagicMock(
        ok=True,
        json=lambda: {
            "user": {
                "name": "Alice",
                "email": "alice@example.com",
                "contact_methods": [
                    {
                        "label": "Default",
                        "address": "alice@work.com",
                    }
                ],
            }
        },
    )

    mock_slack_client.users_lookupByEmail.return_value = {
        "user": {
            "id": "SLACK123",
        }
    }

    assert main.get_em_slack_display_name("U1") == "<@SLACK123>"


@patch("main.slack_client")
@patch("main.get_slack_user_id")
@patch("main.get_on_call_user")
@patch("main.get_on_call_schedule_name")
def test_main(mock_sched, mock_user, mock_slack_id, mock_slack_client):
    """Test the existing V2 notification remains unchanged."""
    mock_sched.return_value = "Test Schedule"
    mock_user.return_value = ("Alice", "alice@work.com")
    mock_slack_id.return_value = "SLACK123"

    with patch.object(
        main,
        "pagerduty_schedule_id",
        "P3MCA8L",
    ):
        main.main()

    mock_slack_client.chat_postMessage.assert_called_with(
        channel=main.slack_channel,
        text="<@SLACK123> is on support for Test Schedule",
    )


@patch("main.slack_client")
@patch("main.get_em_slack_display_name")
@patch("main.get_em_support_users")
def test_main_em_with_shadow(
    mock_get_support_users,
    mock_get_display_name,
    mock_slack_client,
):
    """Test the EM notification when an engineer is shadowing."""
    mock_get_support_users.return_value = (
        "PRIMARY_USER",
        "SHADOW_USER",
    )

    mock_get_display_name.side_effect = [
        "<@PRIMARY>",
        "<@SHADOW>",
    ]

    with patch.object(
        main,
        "pagerduty_schedule_id",
        main.em_data_hub_schedule_id,
    ):
        main.main()

    mock_slack_client.chat_postMessage.assert_called_with(
        channel=main.slack_channel,
        text=(
            "*EM Data Hub support today*\n"
            "<@SHADOW> is on support today (shadowing).\n"
            "<@PRIMARY> is the primary engineer for "
            "guidance and escalation."
        ),
    )


@patch("main.slack_client")
@patch("main.get_em_slack_display_name")
@patch("main.get_em_support_users")
def test_main_em_without_shadow(
    mock_get_support_users,
    mock_get_display_name,
    mock_slack_client,
):
    """Test the EM notification when nobody is shadowing."""
    mock_get_support_users.return_value = (
        "PRIMARY_USER",
        None,
    )

    mock_get_display_name.return_value = "<@PRIMARY>"

    with patch.object(
        main,
        "pagerduty_schedule_id",
        main.em_data_hub_schedule_id,
    ):
        main.main()

    mock_slack_client.chat_postMessage.assert_called_with(
        channel=main.slack_channel,
        text=("*EM Data Hub support today*\n<@PRIMARY> is on support today."),
    )
