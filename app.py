import os
import logging
import slack_sdk

from typing import Set, List
from dotenv import load_dotenv
from slack_bolt import App, Ack

load_dotenv()

loglevel = os.environ.get("LOGLEVEL")
if loglevel == "DEBUG":
    logging.basicConfig(level=logging.DEBUG)
elif loglevel == "INFO":
    logging.basicConfig(level=logging.INFO)
elif loglevel == "WARNING":
    logging.basicConfig(level=logging.WARNING)
elif loglevel == "CRITICAL":
    logging.basicConfig(level=logging.CRITICAL)

# Initializes the app with correct bot token and signing secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# Fetch the user id of the bot
bot_user_id = app.client.auth_test().data["user_id"]
logging.info(f"Bot user id: {bot_user_id}")


################################
# The bot functionality here 👇

def get_message_reactions(
    client: slack_sdk.web.client.WebClient,
    channel: str,
    timestamp: str
) -> dict:
    """Return the reactions of a given threads parent message.

    Args:
        client (slack_sdk.web.client.WebClient): Slack client object
        channel (str): The channel ID
        timestamp (str): The timestamp of the message
    """
    response = client.reactions_get(
        channel=channel, timestamp=timestamp, full=True
    )
    message = response["message"]
    if message.get("reactions") == None:
        return []

    reactions = message["reactions"]
    return reactions


def get_user_ids_of_reacts(wanted_reacts: list, message_reactions: dict) -> Set:
    """Returns a set of the users that has not reacted with either one of the 
    given wanted reactions

    Args:
        wanted_reacts (list): A list of wanted reactions
        message_reactions (dict): A dict of the reactions on a message

    Returns:
        Set: A set of user ids that has reacted
    """
    users = []

    # Extract all the user ids that has reacted with one of the wanted reactions
    for reaction in message_reactions:
        if reaction["name"] in wanted_reacts:
            users += reaction["users"]

    # Turn it into a set to get rid of duplicates
    return set(users)


def get_no_react_user_ids(reacted_users: set, users_in_channel: list) -> list:
    """Returns a list of the user ids that has not reacted

    Args:
        reacted_users (list): A set of the users (that has reacted something on a message)
        users_in_channel (list): A list of the users that should react on the message

    Returns:
        list: A list with the users to remind
    """
    no_react_users = []

    for user in users_in_channel:
        if user not in reacted_users:
            no_react_users.append(user)

    return no_react_users


def get_user_ids_in_channel(client: slack_sdk.web.client.WebClient, channel: str):
    """Returns all the users in the given channel

    Args:
        client (slack_sdk.web.client.WebClient): Slack client object
        channel (str): The channel ID
    """
    response = client.conversations_members(channel=channel)

    users = response["members"]
    cursor = response["response_metadata"]["next_cursor"]
    while cursor != "":
        response = client.conversations_members(channel=channel, cursor=cursor)
        users.extend(response["members"])
        cursor = response["response_metadata"]["next_cursor"]

    users.remove(bot_user_id)  # remove bot from the user list
    logging.info(f"{len(users)} users in channel {channel}")
    return users


def get_all_user_info(client: slack_sdk.web.client.WebClient) -> dict:
    """Returns a dict with al the users for the current workspace. The user ids
    will be the keys of this dict

    Args:
        client (slack_sdk.web.client.WebClient): Slack client

    Returns:
        dict: A dict with all the user with their ids as keys
    """
    response = client.users_list()
    users = {}

    for user in response.data["members"]:
        users[user["id"]] = user

    logging.info(f"Fetched {len(users)} users")
    return users


def get_no_react_user_ids_on_message(
    client: slack_sdk.web.client.WebClient,
    channel_id: str,
    message_ts: str,
    wanted_reactions: list
) -> list:
    """Returns a list of users that have not reacted on a given message with
    one of the given reactions

    Args:
        client (slack_sdk.web.client.WebClient): Slack client
        channel_id (str): The channel_id of the message
        message_ts (str): The message timestamp
        wanted_reactions (list): A list of emoji-names

    Returns:
        list: A list of user ids that have not yet reacted with one of the given
            emojis on the given message
    """

    # Get all reactions on message
    message_reactions: dict = get_message_reactions(client, channel_id,
                                                    message_ts)

    # Get a set of users that have reacted
    users_that_have_reacted = get_user_ids_of_reacts(wanted_reactions,
                                                     message_reactions)

    # Get a list of all the users in the channel
    users_in_channel = get_user_ids_in_channel(client, channel_id)

    # Compute what users need a reminder
    no_react_user_ids = get_no_react_user_ids(users_that_have_reacted,
                                              users_in_channel)

    return no_react_user_ids


def extract_emoji_names(text: str) -> list:
    """Extract the emoji names from a text string where the emojis are
    encapsulated by ::

    Args:
        text (str): Input text

    Returns:
        list: The emoji names
    """
    emojis_tmp = text.replace(" ", "").split(":")
    emojis = [emoji for emoji in emojis_tmp if emoji != ""]
    return emojis


def remind_in_thread(
    client: slack_sdk.web.client.WebClient,
    user: str,
    channel_id: str,
    message_ts: str,
    wanted_reactions: list
):
    """Pings the users that have not reacted with one of the given emojis on
    the given message in that messages thread.

    Args:
        client (slack_sdk.web.client.WebClient): Slack client
        user (str): The invoker user is
        channel_id (str): The channel where the message was posted
        message_ts (str): The message timestamp
        wanted_reactions (list): A list of wanted reactions on the message
    """
    no_react_user_ids = get_no_react_user_ids_on_message(
        client, channel_id, message_ts, wanted_reactions
    )

    if not no_react_user_ids:
        # Everyone has reacted, amazing!

        reactions = "".join(f':{reaction}:' for reaction in wanted_reactions)

        if len(wanted_reactions) == 1:
            text = f"Looks like everyone has reacted with {reactions} on this message"
        else:
            text = f"Looks like everyone has reacted with either one of {reactions} on this message"

        client.chat_postEphemeral(
            channel=channel_id,
            user=user,
            thread_ts=message_ts,
            text=text
        )

    else:
        # Some users have not reacted on the message yet, let's ping them
        pings = " ".join(f"<@{usr}>" for usr in no_react_user_ids)
        text = f"Don't forget! 👆\n{pings}"
        client.chat_postMessage(
            channel=channel_id,
            thread_ts=message_ts,
            text=text
        )

    users = get_all_user_info(client)
    invoke_user = users.get(user)
    logging.info(
        f'{invoke_user["profile"]["real_name"]} invoked the shortcut with the emojis {wanted_reactions}')


def remind_in_dm(
    client: slack_sdk.web.client.WebClient,
    user: str,
    channel_id: str,
    message_ts: str,
    wanted_reactions: list
):
    """Sends a direct message to the users that have not reacted on a message
    with either one of the specified emojis. After that the invoker gets an
    hidden message from the bot containing the users that were notified.

    Args:
        client (slack_sdk.web.client.WebClient): Slack client
        user (str): The invoker user is
        channel_id (str): The channel where the message was posted
        message_ts (str): The message timestamp
        wanted_reactions (list): A list of wanted reactions on the message
    """
    no_react_user_ids = get_no_react_user_ids_on_message(
        client, channel_id, message_ts, wanted_reactions
    )

    # Get the names of all the users
    users = get_all_user_info(client)

    if not no_react_user_ids:
        # Everyone has reacted, amazing!

        reactions = "".join(f':{reaction}:' for reaction in wanted_reactions)

        if len(wanted_reactions) == 1:
            text = f"Looks like everyone has reacted with {reactions} on this message"
        else:
            text = f"Looks like everyone has reacted with either one of {reactions} on this message"

        client.chat_postEphemeral(
            channel=channel_id,
            user=user,
            thread_ts=message_ts,
            text=text
        )

    else:
        # Some users have not reacted on the message yet, let's send them a
        # direct message

        # Get link to message
        message_link = client.chat_getPermalink(
            channel=channel_id, message_ts=message_ts
        )["permalink"]

        pinged_users = []
        for user_id in no_react_user_ids:
            # Ping user
            client.chat_postMessage(
                channel=user_id,
                text=f"Don't forget to react to this <{message_link}|message>"
            )

            # Get username of this user id
            c_user = users.get(user_id)
            if c_user is None:
                pinged_users.append("Unknown user")
                continue

            display_name = c_user["profile"]["display_name"]
            if display_name:
                pinged_users.append(display_name)
            else:
                pinged_users.append(c_user["profile"]["real_name"])

        # Send an Ephemeral message to the user who invoked the shortcut
        text = f'I just pinged these users:\n{", ".join(pinged_users)}'
        client.chat_postEphemeral(
            channel=channel_id,
            user=user,
            thread_ts=message_ts,
            text=text
        )

    invoke_user = users.get(user)
    logging.info(
        f'{invoke_user["profile"]["real_name"]} invoked the command with the emojis {wanted_reactions}')


@app.event("app_mention")
def mention(client: slack_sdk.web.client.WebClient, event: dict):
    """Handles the event that gets triggered when someone pings this bot"""

    # Some variables that are used later on
    channel_id = event["channel"]
    invoker = event["user"]
    text = event["text"].lower()
    thread_ts = event.get("thread_ts")

    if thread_ts is None:
        # App was not mentioned in a thread
        client.chat_postEphemeral(
            channel=channel_id,
            user=invoker,
            text="You have to use me in a thread"
        )

    # The command is composed up of 2 or 3 parts. 2 in case of list and 3
    # in case of reminding the users
    # :emoji: list
    # :emoji: remind here
    # :emoji: remind dm

    if "list" in text:
        # List command invoked
        emojis_tmp = text[text.index(">")+1:text.index("list")]
        wanted_reactions = extract_emoji_names(emojis_tmp)

        no_react_users = get_no_react_user_ids_on_message(
            client, channel_id, thread_ts, wanted_reactions)

        users = get_all_user_info(client)

        user_names = []
        for user_id in no_react_users:
            # Get username of this user id
            c_user = users.get(user_id)
            if c_user is None:
                user_names.append("Unknown user")
                continue

            display_name = c_user["profile"]["display_name"]
            if display_name:
                user_names.append(display_name)
            else:
                user_names.append(c_user["profile"]["real_name"])

        formatted_emojis = "".join(f":{emoji}:" for emoji in wanted_reactions)
        user_names_pretty = ", ".join(user_names)
        text = \
            f"Seems like these people have not yet reacted with "\
            f"{formatted_emojis}: "\
            f"{user_names_pretty}"

        client.chat_postEphemeral(
            channel=channel_id,
            user=invoker,
            thread_ts=thread_ts,
            text=text
        )

    if "remind" in text:
        # Remind command invoked
        # (Yes both can be invoked at the same time)
        emojis_tmp = text[text.index(">")+1:text.index("remind")]
        wanted_reactions = extract_emoji_names(emojis_tmp)
        location = text[text.index("remind")+len("remind"):].strip()

        if location == "here":
            remind_in_thread(
                client,
                invoker,
                channel_id,
                thread_ts,
                wanted_reactions
            )
        elif location == "dm":
            remind_in_dm(
                client,
                invoker,
                channel_id,
                thread_ts,
                wanted_reactions
            )
        else:
            # TODO post ephemeral text with "error"
            logging.warning("A user is trying to do something sketchy")

    logging.debug("Done with request")


# Start the application
if __name__ == "__main__":
    app.start(port=int(os.environ.get("PORT", 3000)))
