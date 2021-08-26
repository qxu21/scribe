
from .text_pinfile import send_pinfile
from .utils import find_message, format_for_feedback, pin_json, msg_to_json, UnionChannelAll
from discord.ext import commands
import discord
import datetime
import os
import json


@commands.command()
async def pin(ctx, *, msg):
    pin_msg = await find_message(msg, ctx.channel)
    if pin_msg is None:
        await ctx.send("Message not found.")
        return
    pin_json(ctx.channel, msg_to_json(pin_msg, False, ctx.message.author))
    await ctx.send(
            "The message `{}` has been pinned.".format(
                format_for_feedback(pin_msg.content)))

@commands.command()
async def quote(ctx, *, msg):
    spl = msg.split("\n")
    if len(spl) != 2:
        await ctx.send((
                "Please quote in the format:\n"
                "`!quote\n"
                "<start message search string or start message id>\n"
                "<end message search string or end message id>`"))
        return
    start_context = await find_message(spl[0], ctx.channel)
    if start_context is None:
        await ctx.send("Start message not found.")
        return
    end_context = await find_message(spl[1], ctx.channel, after=start_context.created_at)
    if end_context is None:
        await ctx.send("End message not found.")
        return
    h = await ctx.channel.history(limit=200,
            before=end_context.created_at + datetime.timedelta(microseconds=1000), 
            after=start_context.created_at - datetime.timedelta(microseconds=1000)).flatten()
    ids = [m.id for m in h]
    if start_context.id not in ids or end_context.id not in ids:
        await ctx.send("The quote selection is too large. Please limit quotes to 200 messages.")
        return
    pin_json(ctx.channel, {
        "is_quote": True,
        "pinner_id": ctx.message.author.id,
        "pin_timestamp": datetime.datetime.utcnow().replace(microsecond=0).isoformat(),
        "messages": [msg_to_json(m, True) for m in h]})
    await ctx.send(
            "The quote starting with `{}` and ending with `{}` has been pinned.".format(
                format_for_feedback(start_context.clean_content),
                format_for_feedback(end_context.clean_content)))

@commands.command()
async def unpin(ctx):
    #put below into a function at some point
    dn = "pins/{}".format(ctx.guild.id)
    fn = "{}.json".format(ctx.channel.id)
    name = os.path.join(dn, fn)
    if not os.path.isdir(dn) or not os.path.isfile(name):
        await ctx.send("No pins have been recorded for this channel.")
        return
    with open(name) as f:
        j = json.load(f)
    #so with step size of -1 it flips then counts
    #doing this backwards to favor unpinning new stuff over old stuff
    success = False
    k = j[::-1]
    for m in k[:5]:
        if "pinner_id" in m and m["pinner_id"] == ctx.message.author.id:
            mt = datetime.datetime.strptime(m['pin_timestamp'], '%Y-%m-%dT%H:%M:%S')
            if datetime.datetime.utcnow() - mt > datetime.timedelta(minutes=10):
                await ctx.send("The last message you pinned is too old to be unpinned!")
                return
            j.remove(m) # may be horribly inefficient
            if m["is_quote"]:
                await ctx.send("Unpinned the quote starting with the message that starts with `{}`".format(
                    format_for_feedback(m['messages'][0]['content'])))
            else:
                await ctx.send("Unpinned the message starting with `{}`.".format(
                    format_for_feedback(m['content'])))
            success = True
            break
    if not success:
        await ctx.send("You have not pinned one of the last five pins.")
        return
    with open(name, 'w') as g:
        json.dump(j, g)

@commands.command()
async def link(ctx):
    guildrow = await ctx.bot.db.fetchrow("""SELECT * 
        FROM guilds
        WHERE id=$1""", ctx.guild.id)
    await ctx.send("https://scribe.fluffybread.net/?pwd={}".format(guildrow['pwd']))

@commands.command()
async def pinfile(ctx, channel: UnionChannelAll = None):
    await send_pinfile(ctx, channel)

@commands.command()
async def omnipinfile(ctx):
    await send_pinfile(ctx, "all")

@pinfile.error
async def pinfile_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("Channel not found.")
    else:
        raise error


@commands.command()
async def help(ctx):
    await ctx.send("https://scribe.fluffybread.net/help")


@commands.command()
async def invite(ctx):
    await ctx.send("Invite Scribe to your server! https://discordapp.com/api/oauth2/authorize?client_id=413082884912578560&permissions=0&scope=bot")