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


async def find_message(
    msg, channel, count=0, silent=False, raw_string=False, after=None
):
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
    # this feels sinful
    # y e a h i'm burning this
    # haha nvm
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
    # ???
    # if ptl_msg is None:
    #    return None

    # we found a message
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
