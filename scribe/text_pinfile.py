import os
import discord
import json
import re


async def send_pinfile(ctx, channel):
    if channel is None:
        channel = ctx.channel
    dn = "pins/{}".format(ctx.guild.id)
    odn = "pins_txt/{}".format(ctx.guild.id)
    if not os.path.isdir(odn):
        os.makedirs(odn)
    if channel != "all":
        fn = "{}.json".format(channel.id)
        fi = os.path.join(dn, fn)
        fo = os.path.join(odn, "scribe-{}-{}.txt".format(ctx.guild.name, channel.name))
        if not os.path.isdir(dn) or not os.path.isfile(fi) or os.path.getsize(fi) == 0:
            await ctx.send("No pins have been recorded for this channel!")
            return
        o = json_file_to_string(fi)
    else:
        fo = os.path.join(odn, "scribe-{}.txt".format(ctx.guild.name))
        o = "\n\n\n".join(
            [
                "--- #{} ---\n\n".format(
                    ctx.guild.get_channel(int(os.path.splitext(f)[0])).name
                )
                + json_file_to_string(os.path.join(dn, f))
                for f in os.listdir(dn)
                if f.endswith(".json") and os.path.splitext(f)[0].isdigit()
            ]
        )
    with open(fo, "w") as f:
        f.write(o)
    await ctx.send(file=discord.File(fp=fo))


# THESE TWO FUNCTIONS HAVE BEEN COPIED INTO GLASS MOSTLY VERBATIM
# IF BIG CHANGES ARE MADE, CONSIDER MODULARIZING THESE
def json_msg_to_text(j):
    if "edited_timestamp" in j and j["edited_timestamp"] is not None:
        e = "[{} edited {}] {}#{}: {}".format(
            j["timestamp"],
            j["edited_timestamp"],
            j["author_name"],
            j["author_discrim"],
            j["content"],
        )
    else:
        e = "[{}] {}#{}: {}".format(
            j["timestamp"], j["author_name"], j["author_discrim"], j["content"]
        )
    if "attachments" in j:
        for a in j["attachments"]:
            e += "\r\nATTACHMENT: " + a
    return e.replace("\n", "\r\n")


def json_file_to_string(fn):
    with open(fn) as fi:
        j = json.load(fi)
    # except json.JSONDecodeError:
    #    await ctx.send("An error occurred retrieving the pinfile.")
    #    raise
    # time to comprehend lists
    return "\r\n\r\n\r\n".join(
        [
            re.sub(
                r"(\r\n){2,}",
                "\r\n\r\n",
                (
                    ("\r\n".join([json_msg_to_text(m) for m in e["messages"]]))
                    if e["is_quote"]
                    else json_msg_to_text(e)
                ),
            )
            for e in j
        ]
    )
