[![PyPi Version](https://img.shields.io/pypi/v/opensam.svg)](https://pypi.python.org/pypi/opensam/)
[![Test Coverage](https://codecov.io/gh/voiio/sam/branch/main/graph/badge.svg)](https://codecov.io/gh/voiio/sam)
[![GitHub License](https://img.shields.io/github/license/voiio/sam)](https://raw.githubusercontent.com/voiio/sam/master/LICENSE)

# Sam – cuz your company is nothing without Sam

![meme](https://repository-images.githubusercontent.com/726003479/24d020ac-3ac5-401c-beae-7a6103c4e7ae)

Sam is a Slack bot that uses OpenAI's ChatGPT model to provide a work-colleague
like experience, right in your Slack workspace.

Everyone in your company has instant access to the most powerful AI companion.

Sam uses OpenAI's assistant API to fine-tune ChatGPT to:

* a specific personality traits,
* provide domain specific knowledge
* and company specific context

to provide a work-colleague like experience.

## Sneak peek of Sam in action

![screenshot.png](screenshot.png)

## Installation
1. Create a new Slack app, as described below.
2. You will also need an OpenAI API key, which you can get from [here](https://platform.openai.com/api-keys).
3. You need to create a OpenAI Assistant [here](https://platform.openai.com/assistants) and copy the assistant ID.
4. With those tokens at the ready, just hit the button below and follow the instructions.

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

### Create a Slack App

1. Create a new Slack App [here](https://api.slack.com/apps?new_app=1).
2. Select `From an app manifest` and enter the URL to the [slack-manifest.yml](slack-manifest.yml) file in this repo.
3. Click `Create App` and then `Install to Workspace`.
4. Copy the `Bot User OAuth Access Token` and paste it into the `SLACK_BOT_TOKEN` field in the Heroku app settings.
5. Create a new `App-Level Tokens` under `Basic Infomation` and copy the token into the `SLACK_APP_TOKEN` field in the Heroku app settings.
