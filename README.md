# PagerDuty Rota Notifier

[![Ministry of Justice Repository Compliance Badge](https://github-community.service.justice.gov.uk/repository-standards/api/pagerduty-rota-notifier/badge)](https://github-community.service.justice.gov.uk/repository-standards/pagerduty-rota-notifier) [![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/ministryofjustice/pagerduty-rota-notifier/badge)](https://scorecard.dev/viewer/?uri=github.com/ministryofjustice/pagerduty-rota-notifier)

[![Open in Dev Container](https://raw.githubusercontent.com/ministryofjustice/.devcontainer/refs/heads/main/contrib/badge.svg)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/ministryofjustice/pagerduty-rota-notifier)

[![Open in Codespace](https://github.com/codespaces/badge.svg)](https://codespaces.new/ministryofjustice/pagerduty-rota-notifier)

This repository contains the code and a scheduled GitHub Actions workflow for sending a notification to a Slack channel

![Example message from Slack](/contrib/example-slack-message.png)

## Using

To use this for your team's PagerDuty rota:

1. Add your PagerDuty rota ID and Slack channel to the matrix in [`.github/workflows/pagerduty-rota-notifier.yml`](.github/workflows/pagerduty-rota-notifier.yml)

1. Invite `@PagerDuty Rota` to your Slack channel

## Configure Slack notifications to correct user

If a user's Slack and PagerDuty email address don't match each other (usually occurs when a user's Slack account is linked to their Justice email and their PagerDuty account to their Digital email), the Slack notifications will not work correctly. To resolve this you need to ensure your Default PagerDuty email matches your Slack account email by doing the following:

1. Log into your PagerDuty account [here](https://moj-digital-tools.pagerduty.com/incidents).

2. Click 'My Profile' in the top-right-hand corner.

3. Under 'Contact Information', update your Default email address to match your Slack account email address and click Save.

4. Future PagerDuty notifications should now correctly tag your correct account in Slack.
