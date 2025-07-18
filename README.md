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

## Development

### Dependabot

#### pre-commit

At the time of writing (17/07/2025), Dependabot doesn't support `pre-commit`

- <https://github.com/dependabot/dependabot-core/issues/1524>

For now, you can run `pre-commit autoupdate`, for example:

```bash
$ pre-commit autoupdate
[https://github.com/pre-commit/pre-commit-hooks] already up to date!
[https://github.com/gitleaks/gitleaks] already up to date!
[https://github.com/zizmorcore/zizmor-pre-commit] already up to date!
[https://github.com/astral-sh/ruff-pre-commit] updating v0.12.1 -> v0.12.4
```

#### `uv` dependency groups

At the time of writing (17/07/2025), Dependabot doesn't support `dependency-groups` in `pyproject.toml` ([PEP 735](https://peps.python.org/pep-0735/)). However, it's actively being worked on:

- <https://github.com/dependabot/dependabot-core/issues/10847>

- <https://github.com/dependabot/dependabot-core/pull/12580>

For now, you can run `uv tree --outdated --depth 1 --only-dev` to show top level `dev` dependencies that are out of date, for example:

```bash
$ uv tree --outdated --depth 1 --only-dev
Resolved 25 packages in 1ms
pagerduty-rota-notifier v0.1.0
├── pre-commit v4.2.0 (group: dev)
├── pytest v8.4.1 (group: dev)
├── ruff v0.11.2 (group: dev) (latest: v0.12.4)
└── zizmor v1.11.0 (group: dev)
```

Then you can update `pyproject.toml` and run `uv sync --upgrade`, for example:

```bash
$ uv sync --upgrade
Installed 1 package in 14ms
 - ruff==0.11.2
 + ruff==0.12.4
```
