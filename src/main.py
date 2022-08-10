#!/usr/bin/env python3
import os

from datetime import datetime
import logging
from pprint import pprint
from slack_bolt import App
from slack_sdk.web import WebClient
from typing import List, Dict, Optional
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

channel_name = 'hot-channels'

client = WebClient(token=os.environ['SLACK_API_TOKEN'])


def get_slack_configs():
    pass


def get_channel_list() -> List[Dict[str, str]]:
    try:
        # Call the conversations.list method using the WebClient
        result = client.conversations_list()
        channel_list: List[Dict[str, str]] = [
            {'id': c['id'], 'name': c['name'],
             'topick_value': c['topic']['value']}
            for c in result['channels'] if c['is_channel']]  # type: ignore
        return channel_list

    except SlackApiError as e:
        logger.error(f'Error fetching conversations: {e}')


def calc_stats():
    pass


def compose_message():
    pass


def post_message():
    pass


def main(*args, **kwargs):

    pass


if __name__ == '__main__':
    main()
