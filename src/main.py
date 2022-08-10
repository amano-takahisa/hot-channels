#!/usr/bin/env python3
import os

from datetime import datetime, timedelta
import logging
from pprint import pprint
from slack_bolt import App
from slack_sdk.web import WebClient
from typing import List, Dict, Optional, Any, Union, NamedTuple
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

CHANNEL_NAME = 'hot-channels'

# Channel names to be excluded from the ranking
# NON_HOT_CHANNELS = ['hot-channels', 'notification']
EXCLUDE_FROM_STAT = ['hot-channels']


def get_slack_configs():
    pass


def get_channel_list(
        client: WebClient) -> List[Dict[str, str]]:  # type: ignore
    try:
        # Call the conversations.list method using the WebClient
        result = client.conversations_list()
        channel_list: List[Dict[str, str]] = [
            {'id': c['id'],
             'name': c['name'],
             'is_member': c['is_member'],
             'topick_value': c['topic']['value']}
            for c in result['channels'] if c['is_channel']]  # type: ignore
        return channel_list

    except SlackApiError as e:
        logger.error(f'Error fetching conversations: {e}')


def join_to_channel(channel_id, client: WebClient):
    client.conversations_join(channel=channel_id)


def get_number_of_messages_today(
        channel_id: str,
        client: WebClient) -> int:
    """
    Because pagination is not yet supported, 100 is returned if the number of
    messages is 100 or more.
    """
    try:
        # Call the conversations.history method using the WebClient
        # conversations.history returns the first 100 messages by default
        # These results are paginated,
        # see: https://api.slack.com/methods/conversations.history$pagination
        result = client.conversations_history(channel=channel_id)
        messages: List[Dict[str, Any]] = result.get('messages')  # type: ignore
        ts_24h_ago = (datetime.today() - timedelta(days=1)).timestamp()
        messages_last_24h = [message for message in messages
                             if float(message['ts']) >= ts_24h_ago]
        return len(messages_last_24h)

    except SlackApiError as e:
        logger.error("Error creating conversation: {}".format(e))


class MessageCount(NamedTuple):
    channel_id: str
    channel_name: str
    channel_topic: str
    message_count: int


def compose_message_blocks(message_counts: List[MessageCount],
                           ) -> List[Dict[str, Any]]:
    n_channels = len(message_counts)
    total_messages = sum([mc.message_count for mc in message_counts])
    message_counts = sorted(message_counts,
                            key=lambda item: getattr(item, 'message_count'),
                            reverse=True)
    stat_blocks = []
    for idx, message_count in enumerate(message_counts):
        if idx == 0:
            icon = ':first_place_medal:'

        else:
            icon = ':tada:'
        stat_block = f'{icon} {idx + 1}. #{message_count.channel_name}'

        stat_blocks.append(stat_block)
    # return stat_messages
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":star2: Today's Active Channel Rankings :star2:"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": ":first_place_medal: #general"
                },
                {
                    "type": "mrkdwn",
                    "text": "30 messagess today"
                }
            ]
        },
        {
            "type": "context",
            "elements": [
                {
                    "text": "xxxxx channel_topic here xxxxx",
                    "type": "mrkdwn"
                }
            ]
        },
        {
            "type": "divider"
        }
    ]

    return blocks


def post_message(channel, client: WebClient, **kwargs):
    try:
        # Call the chat.postMessage method using the WebClient
        result = client.chat_postMessage(channel=channel, **kwargs)
        logger.info(result)
    except SlackApiError as e:
        logger.error(f"Error posting message: {e}")


def main(*args, **kwargs):
    client = WebClient(token=os.environ['SLACK_API_TOKEN'])
    # configs = get_slack_configs()
    channel_list = get_channel_list(client=client)
    hot_channel_id, is_member_hot_channel = [
        (c['id'], c['is_member']) for c in channel_list
        if c['name'] == CHANNEL_NAME][0]

    if is_member_hot_channel is False:
        join_to_channel(channel_id=hot_channel_id, client=client)

    # drop non_hot_channels
    channel_list = [
        c for c in channel_list if c['name'] not in EXCLUDE_FROM_STAT]

    # join to channels
    for channel in channel_list:
        if not channel['is_member']:
            join_to_channel(channel_id=channel['id'], client=client)
            logger.info(f'The bot joined to channel "{channel["name"]}"')

    message_counts: List[MessageCount] = []
    for channel in channel_list:
        n = get_number_of_messages_today(
            channel_id=channel['id'], client=client)
        message_counts.append(
            MessageCount(channel_id=channel['id'],
                         channel_name=channel['name'],
                         channel_topic=channel['topick_value'],
                         message_count=n))

    blocks = compose_message_blocks(message_counts=message_counts)
    pprint(blocks)
    post_message(
        channel=hot_channel_id,

        client=client,
        blocks=blocks,
        text='Hot channel ranking')


if __name__ == '__main__':
    main()
