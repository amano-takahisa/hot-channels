#!/usr/bin/env python3
import os

from datetime import datetime, timedelta
import logging
from pprint import pprint
from slack_bolt import App
from slack_sdk.web import WebClient
from typing import List, Dict, Optional, Any, Union
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


def post_message(channel, client: WebClient, **kwargs):
    try:
        # Call the chat.postMessage method using the WebClient
        result = client.chat_postMessage(channel=channel, **kwargs)
        logger.info(result)
    except SlackApiError as e:
        logger.error(f"Error posting message: {e}")


def main(*args, **kwargs):

    pass


if __name__ == '__main__':
    main()
