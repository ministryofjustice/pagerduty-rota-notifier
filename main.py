"""
This module interacts with PagerDuty and Slack APIs to
fetch on-call schedules and notify the relevant Slack channel.
"""

import os
from time import strftime

from pdpyras import APISession
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

date = strftime("%Y-%m-%d")

pagerduty_schedule_id = os.environ["PAGERDUTY_SCHEDULE_ID"]
pagerduty_token = os.environ["PAGERDUTY_TOKEN"]

slack_channel = os.environ["SLACK_CHANNEL"]
slack_token = os.environ["SLACK_TOKEN"]

pagerduty_client = APISession(pagerduty_token)
slack_client = WebClient(token=slack_token)


def get_on_call_schedule_name():
    """
    Fetches the name of the on-call schedule from PagerDuty.

    Returns:
        str: The name of the on-call schedule.
    """
    response = pagerduty_client.get("/schedules/" + pagerduty_schedule_id)
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
        "/schedules/"
        + pagerduty_schedule_id
        + "/users?since="
        + date
        + "T09%3A00Z&until="
        + date
        + "T17%3A00Z"
    )
    user_name = None
    user_email = None

    if response.ok:
        user_name = response.json()["users"][0]["name"]
        user_email = response.json()["users"][0]["email"]

    return user_name, user_email


def get_slack_user_id():
    """
    Fetches the Slack user IDs of the on-call user based on their email variations.

    Returns:
        list: A list of Slack user IDs for the on-call user.
    """
    user_ids = []

    # get a user's email prefix
    email = get_on_call_user()[1]
    user_email_pref = email.split("@")[0]

    # suffixes for email addresses
    digital_suff = "@justice.gov.uk"
    justice_suff = "@digital.justice.gov.uk"

    # create digital and justice email addresses for user
    justice_email = user_email_pref + digital_suff
    digital_email = user_email_pref + justice_suff

    for email_variant in [justice_email, digital_email]:
        try:
            response = slack_client.users_lookupByEmail(email=email_variant)
            user_ids.append(response["user"]["id"])
        except SlackApiError:
            pass

    return user_ids


def main():
    """
    Main function to post a message to the Slack channel about the on-call user.
    """
    slack_user_ids = get_slack_user_id()

    if not slack_user_ids:
        message = (
            f"{get_on_call_user()[0]} is on support for {get_on_call_schedule_name()}"
        )

    # if a user has 2 Slack accounts against their email prefix, both will receive a notification
    elif len(slack_user_ids) > 1:
        message = (
            f"<@{slack_user_ids[0]}> / <@{slack_user_ids[1]}> is on support for "
            f"{get_on_call_schedule_name()}"
        )
    else:
        message = (
            f"<@{slack_user_ids[0]}> is on support for {get_on_call_schedule_name()}"
        )

    slack_client.chat_postMessage(
        channel=slack_channel,
        text=message,
    )


main()
