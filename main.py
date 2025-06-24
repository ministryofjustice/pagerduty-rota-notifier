"""
This module interacts with PagerDuty and Slack APIs to
fetch on-call schedules and notify the relevant Slack channel.
"""

import os
from time import strftime

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


def get_on_call_schedule_name():
    """
    Fetches the name of the on-call schedule from PagerDuty.

    Returns:
        str: The name of the on-call schedule.
    """
    response = pagerduty_client.get(f"/schedules/{pagerduty_schedule_id}")
    schedule_name = None

    if response.ok:
        schedule_name = response.json()["schedule"]["name"]

    return schedule_name


def get_on_call_user():
    """
    Fetches the name and email of the on-call user from PagerDuty.

    Returns:
        tuple: A tuple containing the name and email of the on-call user.
    """
    response = pagerduty_client.get(
        f"/schedules/{pagerduty_schedule_id}/users?since={date}T09%3A00Z&until={date}T17%3A00Z"
    )
    user_name = None
    user_email = None

    if response.ok:
        user = response.json()["users"][0]
        user_name = user["name"]
        user_id = user["id"]

        # Pull the user again, this time with contact methods included
        user_detail_response = pagerduty_client.get(
            f"/users/{user_id}?include[]=contact_methods"
        )

        if user_detail_response.ok:
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


def main():
    """
    Main function to post a message to the Slack channel about the on-call user.
    """
    if get_slack_user_id() is None:
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
