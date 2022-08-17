#!/usr/bin/env python3
import configparser
import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional

from slack_sdk.errors import SlackApiError
from slack_sdk.web import WebClient

logger = logging.getLogger(__name__)


# NON_HOT_CHANNELS = ['hot-channels', 'notification']

# config_path = Path(__file__).joinpath('../config.ini')
config_path = Path(__file__).parent.parent.joinpath("config.ini")


def get_slack_configs():
    pass


class ChannelMeta(NamedTuple):
    id: str
    is_member: bool
    name: str
    topic_value: str
    purpose_value: str
    num_members: int


def get_channel_metas(client: WebClient) -> List[ChannelMeta]:
    try:
        # Call the conversations.list method using the WebClient
        result = client.conversations_list(
            exclude_archived=True, limit=1000, types="public_channel"
        )
        if result is None:
             raise Exception
        channel_metas: List[ChannelMeta] = [
            ChannelMeta(
                id=c["id"],
                name=c["name"],
                is_member=c["is_member"],
                topic_value=c["topic"]["value"],
                purpose_value=c["purpose"]["value"],
                num_members=c["num_members"],
            )
            for c in result["channels"]
            if c["is_channel"]
        ]  # type: ignore
        return channel_metas

    except SlackApiError as e:
        logger.error(f"Error fetching conversations: {e}")
        raise RuntimeError


def join_to_channel(channel_id, client: WebClient):
    client.conversations_join(channel=channel_id)


def get_number_of_messages_today(channel_id: str, client: WebClient) -> int:
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
        messages: List[Dict[str, Any]] = result.get("messages")  # type: ignore
        ts_24h_ago = (datetime.today() - timedelta(days=1)).timestamp()
        messages_last_24h = [
            message for message in messages if float(message["ts"]) >= ts_24h_ago
        ]
        return len(messages_last_24h)

    except SlackApiError as e:
        logger.error("Error creating conversation: {}".format(e))
        raise RuntimeError


class MessageCount(NamedTuple):
    channel_id: str
    message_count: int


def compose_blocks(
    message_counts: List[MessageCount],
    channel_metas: List[ChannelMeta],
    max_n_channels: Optional[int] = None,
) -> List[Dict[str, Any]]:

    total_messages = sum([mc.message_count for mc in message_counts])
    header_blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":star2: Daily Hot Channel Rankings :star2:",
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "text": (
                        f"Total {total_messages} messages in last 24 hr. |"
                        f"{datetime.today().strftime('%Y-%m-%d (%a) %H:%M %Z')}"
                    ),
                    "type": "mrkdwn",
                }
            ],
        },
        {"type": "divider"},
    ]

    stat_blocks = compose_stat_blocks(
        message_counts=message_counts,
        channel_metas=channel_metas,
        max_n_channels=max_n_channels,
    )
    return header_blocks + stat_blocks


def compose_stat_blocks(
    message_counts: List[MessageCount],
    channel_metas: List[ChannelMeta],
    max_n_channels: Optional[int] = None,
) -> List[Dict[str, Any]]:
    message_counts = sorted(
        message_counts.copy(),
        key=lambda item: getattr(item, "message_count"),
        reverse=True,
    )

    # drop non-message channels and trim size
    message_counts = [mc for mc in message_counts if mc.message_count > 0][
        :max_n_channels
    ]

    n_channels = len(message_counts)

    medals = [
        ":first_place_medal:",
        ":second_place_medal:",
        ":third_place_medal:",
    ]
    medals += [":tada:"] * (n_channels - len(medals))
    medals = medals[:n_channels]

    stat_blocks = []
    for medal, message_count in zip(medals, message_counts):
        num_message = message_count.message_count
        channel_id = message_count.channel_id
        channel_meta = [cm for cm in channel_metas if cm.id == channel_id][0]
        channel_name = channel_meta.name
        channel_members = channel_meta.num_members
        if (channel_topic := channel_meta.topic_value) != "":
            channel_topic = f"*{channel_topic}*"

        channel_purpose = channel_meta.purpose_value

        stat_blocks.extend(
            [
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": (f"{medal}  #{channel_name}\n" f"{channel_topic}"),
                        },
                        {
                            "type": "mrkdwn",
                            "text": (
                                f":speech_balloon: {num_message} "
                                f":people_holding_hands: {channel_members}\n"
                                f"{channel_purpose}"
                            ),
                        },
                    ],
                },
                {"type": "divider"},
            ]
        )

    return stat_blocks


def post_message(channel_id, client: WebClient, **kwargs):
    try:
        # Call the chat.postMessage method using the WebClient
        result = client.chat_postMessage(channel=channel_id, **kwargs)
        logger.info(result)
    except SlackApiError as e:
        logger.error(f"Error posting message: {e}")
        raise RuntimeError


def main():
    # get config
    config = configparser.ConfigParser()
    config.read(config_path)

    # get channel metadatas
    client = WebClient(token=os.environ["SLACK_API_TOKEN"])
    channel_metas = get_channel_metas(client=client)
    channel_name = config.get("channels", "channel_name")
    if channel_name not in [channel_meta.name for channel_meta in channel_metas]:
        raise RuntimeError(
            f"Channel {channel_name} does not exist in your workspace. "
            "Create the channel beforehand."
        )
    hot_channel_id, is_bot_member_in_hot_channel = [
        (channel_meta.id, channel_meta.is_member)
        for channel_meta in channel_metas
        if channel_meta.name == channel_name
    ][0]

    if is_bot_member_in_hot_channel is False:
        logger.info(
            "The bot joined to channel " f'"{config.get("channels", "channel_name")}"'
        )
        join_to_channel(channel_id=hot_channel_id, client=client)

    # Drop non_hot_channels
    channel_metas = [
        channel_meta
        for channel_meta in channel_metas
        if channel_meta.name not in config.get("channels", "exclude_from_stat")
    ]

    # Drop exclude_from_stat channels
    patterns = [
        re.compile(p, re.UNICODE)
        for p in json.loads(config.get("channels", "exclude_from_stat"))
    ]
    channel_metas = [
        channel_meta
        for channel_meta in channel_metas
        if not any([re.fullmatch(pattern, channel_meta.name) for pattern in patterns])
    ]

    # Join to public channels
    if config.getboolean("channels", "auto_join_to_public_channels"):
        # Join to non-member public channels
        for idx, channel_meta in enumerate(channel_metas):
            if not channel_meta.is_member:
                join_to_channel(channel_id=channel_meta.id, client=client)
                channel_metas[idx] = channel_meta._replace(is_member=True)
                logger.info(f'The bot joined to channel "{channel_meta.name}"')
    else:
        # Drop non-member channels
        channel_metas = [
            channel_meta for channel_meta in channel_metas if channel_meta.is_member
        ]

    # Get message counts
    message_counts: List[MessageCount] = [
        MessageCount(
            channel_id=channel_meta.id,
            message_count=get_number_of_messages_today(
                channel_id=channel_meta.id, client=client
            ),
        )
        for channel_meta in channel_metas
    ]

    # compose block
    message_blocks = compose_blocks(
        message_counts=message_counts, channel_metas=channel_metas
    )

    post_message(
        channel_id=hot_channel_id,
        client=client,
        blocks=message_blocks,
        username=config.get("bot appearance", "username"),
        icon_emoji=config.get("bot appearance", "icon_emoji"),
        text="Hot channel ranking",
    )


if __name__ == "__main__":
    main()
