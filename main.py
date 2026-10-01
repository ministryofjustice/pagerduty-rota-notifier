"""
This module interacts with PagerDuty and Slack APIs to
fetch on-call schedules and notify the relevant Slack channel.
"""

import os
from datetime import datetime, time, timedelta
from time import strftime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from pagerduty import RestApiV2Client
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

date = strftime("%Y-%m-%d")

pagerduty_schedule_id = os.environ["PAGERDUTY_SCHEDULE_ID"]
pagerduty_token = os.environ["PAGERDUTY_TOKEN"]

slack_channel = os.environ["SLACK_CHANNEL"]
slack_token = os.environ["SLACK_TOKEN"]

pagerduty_client = RestApiV2Client(pagerduty_token)
slack_client = WebClient(token=slack_token)

# EM Data Hub shift-based V3 schedule.
em_data_hub_schedule_id = "P4M9I3U"


def get_on_call_schedule_name():
    """
    Fetches the name of the on-call schedule from PagerDuty.

    Returns:
        str: The name of the on-call schedule.
    """
    response = pagerduty_client.get(f"/schedules/{pagerduty_schedule_id}")
    schedule_name = None

    # use getattr to check which attributes are returned in the response.
    # is_success works with newer httpx style.
    if getattr(response, "ok", None) or getattr(response, "is_success", None):
        schedule_name = response.json()["schedule"]["name"]

    return schedule_name


def get_on_call_user():
    """
    Fetches the name and email of the on-call user from PagerDuty.

    Returns:
        tuple: A tuple containing the name and email of the on-call user.
    """
    params = {"since": f"{date}T09:00Z", "until": f"{date}T17:00Z"}
    query_string = urlencode(params)
    response = pagerduty_client.get(
        f"/schedules/{pagerduty_schedule_id}/users?{query_string}"
    )
    user_name = None
    user_email = None

    # use getattr to check which attributes are returned in the response.
    # is_success works with newer httpx style.
    if getattr(response, "ok", None) or getattr(response, "is_success", None):
        user = response.json()["users"][0]
        user_name = user["name"]
        user_id = user["id"]

        # Pull the user again, this time with contact methods included
        user_detail_response = pagerduty_client.get(
            f"/users/{user_id}?include[]=contact_methods"
        )

        # use getattr to check which attributes are returned in the response.
        # is_success works with newer httpx style.
        if getattr(user_detail_response, "ok", None) or getattr(
            user_detail_response, "is_success", None
        ):
            # Look for the e‑mail address whose contact‑method label is “Default”
            for cm in user_detail_response.json()["user"].get("contact_methods", []):
                if cm.get("label") == "Default":
                    # “address” holds the e‑mail value
                    user_email = cm.get("address")
                    break

        # If no “Default” label was found, fall back to the user’s primary e‑mail
        if user_email is None:
            user_email = user.get("email")

    return user_name, user_email


def get_slack_user_id():
    """
    Fetches the Slack user ID of the on-call user based on their email.

    Returns:
        str: The Slack user ID of the on-call user.
    """
    user_id = None

    try:
        response = slack_client.users_lookupByEmail(email=get_on_call_user()[1])
        user_id = response["user"]["id"]
    except SlackApiError:
        pass

    return user_id


# EM V3 schedule migration
def get_em_support_users():
    """
    Fetches the primary and optional shadowing engineer from the
    EM Data Hub V3 shift-based schedule.

    Returns:
        tuple: PagerDuty user IDs for the primary and shadowing engineers.
    """
    london_timezone = ZoneInfo("Europe/London")

    support_start = datetime.combine(
        datetime.now(london_timezone).date(),
        time(hour=9),
        tzinfo=london_timezone,
    )
    support_end = support_start + timedelta(minutes=1)

    params = {
        "since": support_start.isoformat(),
        "until": support_end.isoformat(),
        "time_zone": "Europe/London",
        "include[]": "final_schedule",
    }
    query_string = urlencode(params)

    response = pagerduty_client.get(
        f"/v3/schedules/{pagerduty_schedule_id}?{query_string}"
    )

    if not (getattr(response, "ok", None) or getattr(response, "is_success", None)):
        return None, None

    schedule = response.json()["schedule"]

    shadow_rotation_ids = set()

    for rotation in schedule.get("rotations", []):
        for event in rotation.get("events", []):
            if event.get("name", "").startswith("Shadow "):
                shadow_rotation_ids.add(rotation["id"])
                break

    primary_user_id = None
    shadow_user_id = None

    assignments = schedule.get("final_schedule", {}).get(
        "computed_shift_assignments",
        [],
    )

    for assignment in assignments:
        member = assignment.get("member") or {}

        if member.get("type") != "user_member":
            continue

        user_id = member.get("user_id")
        rotation_id = (assignment.get("source") or {}).get("rotation_id")

        if not user_id:
            continue

        if rotation_id in shadow_rotation_ids:
            shadow_user_id = user_id
        else:
            primary_user_id = user_id

    return primary_user_id, shadow_user_id


def get_em_slack_display_name(user_id):
    """
    Fetches a PagerDuty user and returns their Slack mention when available.

    Returns:
        str: Slack mention or PagerDuty user name.
    """
    response = pagerduty_client.get(f"/users/{user_id}?include[]=contact_methods")

    if not (getattr(response, "ok", None) or getattr(response, "is_success", None)):
        return None

    user = response.json()["user"]

    user_name = user.get("name")
    user_email = None

    for cm in user.get("contact_methods", []):
        if cm.get("label") == "Default":
            user_email = cm.get("address")
            break

    if user_email is None:
        user_email = user.get("email")

    if user_email is not None:
        try:
            slack_response = slack_client.users_lookupByEmail(email=user_email)
            return f"<@{slack_response['user']['id']}>"
        except SlackApiError:
            pass

    return user_name


def main():
    """
    Main function to post a message to the Slack channel about the on-call user.
    """

    # EM Data Hub uses a V3 shift-based schedule which can have both a
    # primary engineer and a shadowing engineer.
    if pagerduty_schedule_id == em_data_hub_schedule_id:
        primary_user_id, shadow_user_id = get_em_support_users()

        if primary_user_id is None:
            raise RuntimeError("No primary EM Data Hub support engineer found")

        primary_user = get_em_slack_display_name(primary_user_id)

        if shadow_user_id is not None:
            shadow_user = get_em_slack_display_name(shadow_user_id)

            message = (
                "*EM Data Hub support today*\n"
                f"{shadow_user} is on support today (shadowing).\n"
                f"{primary_user} is the primary engineer for "
                "guidance and escalation."
            )
        else:
            message = (
                f"*EM Data Hub support today*\n{primary_user} is on support today."
            )

    # Existing behaviour for all legacy V2 schedules.
    elif get_slack_user_id() is None:
        message = (
            f"{get_on_call_user()[0]} is on support for {get_on_call_schedule_name()}"
        )
    else:
        message = (
            f"<@{get_slack_user_id()}> is on support for {get_on_call_schedule_name()}"
        )

    slack_client.chat_postMessage(
        channel=slack_channel,
        text=message,
    )


if __name__ == "__main__":
    main()
