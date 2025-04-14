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
        tuple: A tuple containing the name, email and the email prefix
        of the on-call user.
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
    user_email_pref = None

    if response.ok:
        user_name = response.json()["users"][0]["name"]
        user_email = response.json()["users"][0]["email"]

        # remove a user's email suffix and remove all non-alphabetic characters,
        # this helps to find users in Slack who have an email which differs from
        # the one in PagerDuty
        user_email_pref = user_email.split("@")[0].lower()
        user_email_pref = "".join(filter(str.isalpha, user_email_pref))

    return user_name, user_email, user_email_pref


def get_channel_user_details():
    """
    Retrieves details for each user in a specified Slack channel.

    Returns:
        dict: A dictionary keyed by Slack user ID, containing:
            {
                "name": str,
                "email": str,
                "id": str,
                "user_email_pref": str
            }
          If an error occurs, returns an empty dict.
    """
    try:
        response = slack_client.conversations_members(channel=slack_channel)
        member_ids = response["members"]
    except SlackApiError as e:
        print(f"Error fetching members: {e.response['error']}")
        return {}

    members_info = {}
    for user_id in member_ids:
        try:
            user_info = slack_client.users_info(user=user_id)
            profile = user_info["user"]["profile"]
            name = profile.get("real_name", "Unknown")
            email = profile.get("email", "No email").lower()

            # Simplify email prefix by removing non-alphabetic chars
            user_email_pref = email.split("@")[0]
            user_email_pref = "".join(filter(str.isalpha, user_email_pref))

            members_info[user_id] = {
                "name": name,
                "email": email,
                "id": user_info["user"]["id"],
                "user_email_pref": user_email_pref
            }
        except SlackApiError as e:
            print(f"Error fetching user info for user {user_id}: {e.response['error']}")
        except KeyError as e:
            print(f"KeyError parsing Slack user info for user {user_id}: {e}")

    return members_info


def get_slack_user_id():
    """
    Identifies the Slack user ID of the on-call user based on PagerDuty data.

    This function retrieves the on-call user's email from PagerDuty and attempts 
    to match it with the email addresses of Slack channel members. If an exact 
    match is not found, it tries to match a simplified version of the email prefix.

    Returns:
        str or None: The Slack user ID of the on-call user if a match is found, 
        otherwise None.
    """
    # get the on-call user from PagerDuty
    _, user_email, user_email_pref = get_on_call_user()

    # return None if the user_email is not found
    if not user_email:
        return None

    # get slack channel user details
    user_details = get_channel_user_details()

    # initially try to find a match by the exact email
    for slack_user_id, info in user_details.items():
        if info["email"].lower() == user_email.lower():
            return slack_user_id

    # if no exact email match, then try matching the simplified email prefix
    if user_email_pref:
        for slack_user_id, info in user_details.items():
            if info["user_email_pref"] == user_email_pref:
                return slack_user_id

    return None

def main():
    """
    Main function to post a message to the Slack channel about the on-call user.
    """
    # find the Slack user ID based on the currently on-call PagerDuty user
    oncall_slack_user_id = get_slack_user_id()

    # get on call user and schedule name
    user_name, _, _ = get_on_call_user()
    schedule_name = get_on_call_schedule_name()

    # prep the message depending on whether we found a matching Slack user
    if oncall_slack_user_id is None:
        message = f"{user_name} is on support for {schedule_name}"
    else:
        message = f"<@{oncall_slack_user_id}> is on support for {schedule_name}"

    slack_client.chat_postMessage(
        channel=slack_channel,
        text=message,
    )

main()
