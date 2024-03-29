import discord
from discord.ext import commands
import datetime
import os
import json


class UnionChannelAll(commands.TextChannelConverter):
    async def convert(self, ctx, arg):
        if arg == "all":
            if any([c.name == "all" for c in ctx.guild.text_channels]):
                await ctx.send(
                    """This server has a channel named #all. \
                    If you wanted to request the serverwide pinfile, try !omnipinfile instead."""
                )
                return await super().convert(ctx, arg)
            return "all"
        else:
            return await super().convert(ctx, arg)


async def find_message(msg, channel, after=None):
    # msg is either a string to search for *or* a message id *or* a list of words
    # *or* an int of messages to go forward/back from UPDATE: maybe don't do this
    # was i tired when i wrote this???

    if type(msg) == str:
        try:
            search = int(msg.split()[0])
        except ValueError:
            search = msg
    elif type(msg) == int:
        search = msg
    else:
        raise TypeError

    if type(search) == int:
        try:
            message = await channel.fetch_message(search)
            return message
        except discord.NotFound:
            search = str(search)
    # id msgs were handled above, so here we have a string that needs to be searched
    ptl_msg = await channel.history(after=after).find(
        lambda m: (m.content.startswith(search) or m.clean_content.startswith(search))
        and m.channel == channel
    )
    return ptl_msg


def msg_to_json(m, isquote=False, pinner=None):
    d = {
        "id": m.id,
        "timestamp": m.created_at.replace(microsecond=0).isoformat(),
        "edited_timestamp": (
            m.edited_at.replace(microsecond=0).isoformat()
            if m.edited_at is not None
            else None
        ),
        "author_name": m.author.name,
        "author_discrim": m.author.discriminator,
        "content": m.clean_content,
        "attachments": [a.url for a in m.attachments],
    }
    if not isquote:
        d["pinner_id"] = (
            pinner.id if pinner is not None else None
        )  # maybe used dict.extend()
        d["pin_timestamp"] = (
            datetime.datetime.utcnow().replace(microsecond=0).isoformat()
        )
        d["is_quote"] = False
    return d


def pin_json(channel, j):
    # OPTIMIZATION POTENTIAL: make this async
    # ripped from pin_text and modified beyond recognition kinda
    dn = "pins/{}".format(channel.guild.id)
    fn = "{}.json".format(channel.id)
    f = os.path.join(dn, fn)
    if not os.path.isdir(dn):
        os.makedirs(dn)
    try:
        # it's okay if this throws
        if os.path.getsize(f) != 0:
            with open(f) as fi:
                jobj = json.load(fi)
        else:
            jobj = []
    except FileNotFoundError:
        jobj = []
    except json.JSONDecodeError:
        print("PANIC! DECODE ERROR!")
        channel.send("An error occurred in pinning.")
        raise
    jobj.append(j)
    with open(f, "w") as fo:
        json.dump(jobj, fo)


async def create_pin(ctx):
    # will return the ID of the newly created pin
    return await ctx.bot.db.fetchval(
        """INSERT INTO pins (guild, channel, pinner)
        VALUES ($1, $2, $3)
        RETURNING id;""",
        ctx.guild.id,
        ctx.channel.id,
        ctx.message.author.id,
    )


async def add_message(db, message, pin_id, is_reply=False):
    if (
        message.type == discord.MessageType.default
        and message.reference
        and message.reference.message_id
    ):
        reply = await message.channel.fetch_message(message.reference.message_id)
    else:
        reply = None
    if reply:
        # recursively add the reply first, because the reply
        # may be out of ordinary pin scope
        await add_message(db, reply, pin_id, is_reply=True)

    # ON CONFLICT DO NOTHING in the event a message is pinned twice
    # in the same pin
    await db.execute(
        """
        INSERT INTO messages
        (id, author, created_at, edited_at, content, url, reply)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT DO NOTHING;
        """,
        message.id,
        message.author.id,
        message.created_at.replace(microsecond=0),
        (message.edited_at.replace(microsecond=0) if message.edited_at else None),
        message.clean_content,
        message.jump_url,
        (reply.id if reply else None),
    )
    await db.execute(
        """
        INSERT INTO messages_pins
        (message, pin, is_reply)
        VALUES ($1, $2, $3);
        """,
        message.id,
        pin_id,
        is_reply,
    )
    for attachment in message.attachments:
        await db.execute(
            """
            INSERT INTO attachments
            (message, url)
            VALUES ($1, $2);
            """,
            message.id,
            attachment.url,
        )


def format_for_feedback(s):
    # if i had figured out to chain replace calls earlier
    if s == "":
        return "[no message content]"
    s = s.replace("`", "").replace("\n", " ")
    s = s.strip()
    if len(s) <= 20:
        return s
    else:
        return s[:20] + "..."
