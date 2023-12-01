# Sam – Your favorit colleague

A GPT based slack bot trained to specific personalities and use cases.

Highlights:
* Customizable personality
* Context aware and domain specific
* Mention in a channel to get a response
* Send a DM to get a response
* Send images, spreadsheets, and other files to get a response

Sam uses OpenAI's assistant API to align ChatGPT to a specific personality traits,
provide domain specific knowledge and context to provide a work-colleague like
experience.

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
