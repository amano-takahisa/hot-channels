#!/usr/bin/env python3
import re
import json
import os

from datetime import datetime, timedelta
import configparser
import logging
from pprint import pprint
from slack_bolt import App
from slack_sdk.web import WebClient
from typing import List, Dict, Optional, Any, Union, NamedTuple
from slack_sdk.errors import SlackApiError
from pathlib import Path

logger = logging.getLogger(__name__)


# NON_HOT_CHANNELS = ['hot-channels', 'notification']

# config_path = Path(__file__).joinpath('../config.ini')
config_path = Path(__file__).parent.parent.joinpath('config.ini')


def get_slack_configs():
    pass


class ChannelMeta(NamedTuple):
    id: str
    is_member: bool
    name: str
    topick_value: str
    purpose_value: str


def get_channel_metas(
        client: WebClient) -> List[ChannelMeta]:
    try:
        # Call the conversations.list method using the WebClient
        result = client.conversations_list(
            exclude_archived=True,
            limit=1000,
            types='public_channel'
        )
        channel_metas: List[ChannelMeta] = [
            ChannelMeta(
                id=c['id'],
                name=c['name'],
                is_member=c['is_member'],
                topick_value=c['topic']['value'],
                purpose_value=c['purpose']['value'])
            for c in result['channels'] if c['is_channel']]  # type: ignore
        return channel_metas

    except SlackApiError as e:
        logger.error(f'Error fetching conversations: {e}')
        raise RuntimeError


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
        # TODO: implement pagenation to get more than 100 messages per day
        result = client.conversations_history(channel=channel_id)
        messages: List[Dict[str, Any]] = result.get('messages')  # type: ignore
        ts_24h_ago = (datetime.today() - timedelta(days=1)).timestamp()
        messages_last_24h = [message for message in messages
                             if float(message['ts']) >= ts_24h_ago]
        return len(messages_last_24h)

    except SlackApiError as e:
        logger.error("Error creating conversation: {}".format(e))
        raise RuntimeError


class MessageCount(NamedTuple):
    channel_id: str
    message_count: int


def compose_message_blocks(
    message_counts: List[MessageCount],
    channel_metas: List[ChannelMeta]
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
        # stat_block = f'{icon} {idx + 1}. #{message_count.channel_name}'

        # stat_blocks.append(stat_block)
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
        raise RuntimeError


def main(*args, **kwargs):
    # get config
    config = configparser.ConfigParser()
    config.read(config_path)

    # get channel metadatas
    client = WebClient(token=os.environ['SLACK_API_TOKEN'])
    channel_metas = get_channel_metas(client=client)
    channel_name = config.get('channels', 'channel_name')
    if channel_name not in [
            channel_meta.name for channel_meta in channel_metas]:
        raise RuntimeError(
            f'Channel {channel_name} does not exist in your workspace. '
            'Create the channel beforehand.')
    hot_channel_id, is_bot_member_in_hot_channel = [
        (channel_meta.id, channel_meta.is_member) for channel_meta
        in channel_metas if channel_meta.name == channel_name][0]

    if is_bot_member_in_hot_channel is False:
        logger.info('The bot joined to channel '
                    f'"{config.get("channels", "channel_name")}"')
        join_to_channel(channel_id=hot_channel_id, client=client)

    # Drop non_hot_channels
    channel_metas = [
        channel_meta for channel_meta in channel_metas if channel_meta.name
        not in config.get('channels', 'exclude_from_stat')]

    # Drop exclude_from_stat channels
    patterns = [
        re.compile(p, re.UNICODE) for p
        in json.loads(config.get('channels', 'exclude_from_stat'))]
    channel_metas = [channel_meta for channel_meta in channel_metas if not any(
        [re.fullmatch(pattern, channel_meta.name) for pattern in patterns])]

    # Join to public channels
    if config.getboolean('channels', 'auto_join_to_public_channels'):
        # Join to non-member public channels
        for idx, channel_meta in enumerate(channel_metas):
            if not channel_meta.is_member:
                join_to_channel(channel_id=channel_meta.id, client=client)
                channel_metas[idx] = channel_meta._replace(is_member=True)
                logger.info(f'The bot joined to channel "{channel_meta.name}"')
    else:
        # Drop non-member channels
        channel_metas = [
            channel_meta for channel_meta in channel_metas
            if channel_meta.is_member]

    pprint(channel_metas)
    # Getch message counts
    message_counts: List[MessageCount] = [
        MessageCount(channel_id=channel_meta.id,
                     message_count=get_number_of_messages_today(
                         channel_id=channel_meta.id, client=client))
        for channel_meta in channel_metas]
    pprint(message_counts)

    exit()
    blocks = compose_message_blocks(message_counts=message_counts)
    # pprint(blocks)
    # post_message(
    #     channel=hot_channel_id,

    #     client=client,
    #     blocks=blocks,
    #     text='Hot channel ranking')


if __name__ == '__main__':
    main()
