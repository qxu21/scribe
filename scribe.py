import discord
from discord.ext import commands
import datetime
import time
import asyncio
import types
import random
import os
import os.path
import sys
import re

# TODO:
# 2. reactions?
# 4. pincaps
# 7. pin actual pins
# allow a command to rollback most recent pin
# tell to use devmode
# allow messages that start with mentions
# add !pun

# MAYBEDO:
# create its own directories

scribe = commands.Bot(command_prefix='!')
scribe.remove_command("help")

async def find_message(msg, channel, count=0, silent=False, raw_string=False):
    # msg is either a string to search for *or* a message id *or* a list of words
    # *or* an int of messages to go forward/back from UPDATE: maybe don't do this
    # was i tired when i wrote this???
    
    #what is below
    #if type(msg) == discord.Message:
    #    msg = msg.content

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
            message = await channel.get_message(search)
            return message
        except discord.NotFound:
            return None
    else:
        # id msgs were handled above, so here we have a string that needs to be searched
        ptl_msg = await channel.history().find(
                lambda m: (m.content.startswith(search) or m.clean_content.startswith(search)) and m.channel == channel)
        #???
        #if ptl_msg is None:
        #    return None

        # we found a message
        return ptl_msg

def pretty_print(m):
    s = ""
    if m.edited_at is None:
        s += "[{}] {}#{}: {}\n".format(
                m.created_at.replace(microsecond=0).isoformat(),
                m.author.name,
                m.author.discriminator,
                m.clean_content)
    else:
        s += "[{} edited {}] {}#{}: {}\n".format(
                m.created_at.replace(microsecond=0).isoformat(),
                m.edited_at.replace(microsecond=0).isoformat(),
                m.author.name,
                m.author.discriminator,
                m.clean_content)
    if m.attachments != []:
        for a in m.attachments:
            s += "ATTACHMENT: {}\n".format(a.url)
    return s


def pin_message(message):
    if type(message) == discord.Message:
        pin_text(message.channel, pretty_print(message))
    elif type(message) == list:
        for m in message:
            pin_text(message.channel, pretty_print(m)) # errors probably aaa rushhhhh

def pin_text(channel, text):
    # OPTIMIZATION POTENTIAL: make this async
    # still does not support dms - channel must be GuildChannel
    # if multiple messages need ot be pinned, pass a list, since the file is opened for each call
    # sanitize text with regex
    text = re.sub(r"\n{3,}", "\n\n", text)
    dn = "pins/{}".format(channel.guild.id)
    fn = "{}.txt".format(channel.id)
    if not os.path.isdir(dn):
        os.makedirs(dn)
    with open(os.path.join(dn,fn), 'a') as f:
        if type(text) == str:
            f.write(text + "\n\n\n")
        elif type(text) == list:
            for l in text:
                f.write(l + "\n\n\n")

"""async def on_guild_join(guild):
    for channel in guild.text_channels:
        pinlist = []
        pin_ids = []
        pins = await channel.pins()
        for pin in pins:
            pinlist.append(pretty_print(pin))
            pin_ids.append(pin.id)
        pin_message(channel, pinlist)
        # push pickled pin_ids to database

async def on_guild_channel_pins_update(channel, last_pin_time):
    # unpickle pins from database
    current_pins = await channel.pins()
    if len(previous_pins) > len(current_pins):
        # currently no unpinning functionality
        return
    # obtain the odd pin out - how?
    # pin_message() odd pin - maybe add self.
    """

def format_for_feedback(string):
    # if i had figured out to chain replace calls earlier
    string = string.replace('`','').replace('\n', ' ')
    string = string.strip()
    if len(string) < 20:
        return string
    else:
        return string[:20] + "..."

    # main command for this bot is gonna be !pin
    if ctx.channel.permissions_for(ctx.guild.me).send_messages == False:
        # no send, no pin
        return

@scribe.command()
async def pin(ctx, *, msg):
    pin_msg = await find_message(msg, ctx.channel)
    if pin_msg is None:
        await ctx.send("Message not found.")
        return
    pin_string = ""
    pin_string = pretty_print(pin_msg)
    pin_text(ctx.channel, pin_string)
    await ctx.send(
            "The message `{}` has been pinned.".format(
                format_for_feedback(pin_msg.content)))

@scribe.command()
async def quote(ctx, *, msg):
    spl = msg.split("\n")
    if len(spl) != 2:
        await ctx.send((
                "Please quote in the format:\n"
                "`!quote\n"
                "<start message search string>\n"
                "<end message search string>`"))
        return
    start_context = await find_message(spl[0], ctx.channel)
    if start_context is None:
        await ctx.send("Start message not found.")
        return
    end_context = await find_message(spl[1], ctx.channel)
    if end_context is None:
        await ctx.send("End message not found.")
        return
    if end_context.created_at < start_context.created_at:
        # TOASK: abort or silently swap?
        tmp = end_context
        end_context = start_context
        start_context = tmp
    pin_string = ""
    async for m in ctx.channel.history(limit=60,
            before=end_context.created_at + datetime.timedelta(microseconds=1000), 
            after=start_context.created_at - datetime.timedelta(microseconds=1000)): 
        pin_string += pretty_print(m)
    pin_text(ctx.channel, pin_string)
    await ctx.send(
            "The quote starting with `{}` and ending with `{}` has been pinned.".format(
                format_for_feedback(start_context.clean_content),
                format_for_feedback(end_context.clean_content)))

#@scribe.command()
#async def unpin(ctx):
#    dn = "pins/{}".format(ctx.guild.id)
#    fn = "{}.txt".format(ctx.channel.id)
#    if not os.path.isdir(dn) or not os.path.isfile(os.path.join(dn, fn)):
#        await ctx.send("No pins have been recorded for this channel!")
#        return
    # how to get last message without breaking sanitization

@scribe.command()
async def pinfile(ctx, channel: discord.TextChannel = None):
    #if len(ctx.message.channel_mentions) == 1:
    #    cn = ctx.message.channel_mentions[0]
    #elif len(ctx.message.channel_mentions) > 1:
    #    await ctx.send("You can only ask for one channel!")
    #    return
    #else:
    #    cn = ctx.channel
    if channel is None:
        channel = ctx.channel
    dn = "pins/{}".format(ctx.guild.id)
    fn = "{}.txt".format(channel.id)
    filename = "scribe-{}-{}-{}.txt".format(
            ctx.guild.name,
            channel.name,
            datetime.datetime.utcnow().replace(microsecond=0).isoformat())
    if not os.path.isdir(dn) or not os.path.isfile(os.path.join(dn, fn)):
        await ctx.send("No pins have been recorded for this channel!")
        return
    await ctx.send(
            file=discord.File(
                fp=os.path.join(dn, fn),
                filename=filename))

@pinfile.error
async def pinfile_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("Channel not found.")
    else:
        raise error


@scribe.command()
async def help(ctx):
    await ctx.send(
        "Use `!pin <first few words of message>` to pin a single message.\n\n" \
        "`!quote\n<first few words of start message>\n<first few words of end message>`\npins a message block.\n\n" \
        "The bot also accepts message IDs if you know how to find them.\n\n" \
        "Use `!pinfile` to grab the current channel's pin file, or `!pinfile #channel` to obtain another channel's pin file.\n\n" \
        "Use `!help` to display this help message.\n\n" \
        "Use `!invite` to obtain an invite for Scribe.")

@scribe.command()
async def invite(ctx):
    await ctx.send("Invite Scribe to your server! https://discordapp.com/api/oauth2/authorize?client_id=413082884912578560&permissions=0&scope=bot")

if sys.argv[1] in ("dev", "test"):
    scribe.run('NDE2MDUxMjQ2Nzc2OTc1MzYx.DW-1cw.Mu2snuR0kfsCnezGPcA4BoLiB7c')
elif sys.argv[1] in ("prod", "production"):
    scribe.run('NDEzMDgyODg0OTEyNTc4NTYw.DWTo9Q.ZW29xMylWrV5uS1qKgHPqlcVQGM')
