# Setup

## Create slack app

https://github.com/slackapi/python-slack-sdk/tree/main/tutorial

1. From [Create New App](https://api.slack.com/apps?new_app=1), select "from scratch". Set 'hot_channel_bot'
   as name, pick a workspace which you want to deploy, and click 'create' button.
2. Setup OAuth & Permissions
    1. Select 'OAuth & Permissions' from left menu.
    2. In 'Scope' > 'Bot Token Scopes' section, give following OAuth Scopes.
        - channels:history (To count messages in the channel.)
        - channels:join (Bot needs to join to the channel to get number of messages.)
        - chat:write (To post ranking messages.)
        - channels:read (To get list of channels)
3. Install the bot to your workspace from left side menu Setting > Install app > Install Workspace. 
4. Copy Bot User OAuth Token which start from  `xoxb-`.

## Config the bot
The name of the channel on which the bot will count the number of messages, etc. can be tweaked by editing
the `config.ini` file.

## Try the bot from your local machine
### Install dependency package
```
pip install -r requirements.txt
```

Run following command. (Replace xoxb-... part to your bot user OAuth Token you copied.)
```bash
SLACK_API_TOKEN=xoxb-... ./src/main.py
```
## Run the bot from Github Actions

## add SLACK_API_TOKEN to env

```bash
export SLACK_API_TOKEN=xoxb-.....
```
