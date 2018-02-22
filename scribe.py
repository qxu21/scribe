import discord
import datetime
import time
import asyncio
import types
import random
import os
import os.path
import sys

# TODO:
# 2. reactions
# 3. if scribetest is in there don't talk

# MAYBEDO:
# create its own directories

class Scribe(discord.Client):
    #pinning = []

    async def find_message(self, msg, channel, count=0, silent=False, raw_string=False):
        # msg is either a string to search for *or* a message id *or* a list of words
        # *or* an int of messages to go forward/back from UPDATE: maybe don't do this
        # was i tired when i wrote this???
        if type(msg) == discord.Message:
            msg = msg.content
        if type(msg) == str and (msg.split()[0] == "!pin" or msg.split()[0] == "!quote"):
            # chop off !pin if it exists
            msg = " ".join(msg.split()[1:])
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
                if not silent:
                    await channel.send(
                        "MESSAGE FOUND: The message with ID {} and contents \"{}\" corresponds to the given ID."
                        .format(message.id, message.content))
                return message
            except discord.NotFound:
                if not silent:
                    await channel.send("INVALID MESSAGE ID: Message ID not found in this channel.")
                return None
        else:
            # id msgs were handled above, so here we have a string that needs to be searched
            ptl_msg = await channel.history().find(
                    lambda m: m.content.startswith(search) and m.channel == channel)
            if ptl_msg is None:
                if not silent:
                    await channel.send("INVALID SEARCH STRING: A message with the contents {} cannot be found in this channel."
                            .format(search))
                return None
            # we found a message
            if not silent:
                await channel.send(
                        "MESSAGE FOUND: The message with ID {} and contents \"{}\" corresponds to the search string."
                        .format(ptl_msg.id, ptl_msg.content))
            return ptl_msg

    async def prompt(self, channel, cmd, pinner, prompt, check=None, check_fail=""):
        await channel.send(prompt)
        while True:
            request = await self.wait_for(
                    'message',
                    check=lambda m: m.author == pinner and m.channel == channel and (m.content.startswith(cmd) or m.content.startswith("!stop")))
            if request.content.startswith("!stop"):
                await channel.send("Aborting pin attempt.")
                return
            msg = await self.find_message(request.content.split(' ', 1)[1], channel)
            if msg is None:
                await channel.send("Please try !pinning again or abort the pin with !stop.")
                continue
            if check is not None and not check(msg):
                # check must be a function that accepts a Message and returns a boolean
                await channel.send("MESSAGE INVALID: " + check_fail + " Please try !pinning again or abort the pin with !stop.")
                continue
            return msg

    async def pretty_print(self, m):
        if m.edited_at is None:
            return "[{}] {}#{}: {}\n".format(
                    m.created_at.replace(microsecond=0).isoformat(),
                    m.author.name,
                    m.author.discriminator,
                    m.content)
        else:
            return "[{} edited {}] {}#{}: {}\n".format(
                    m.created_at.replace(microsecond=0).isoformat(),
                    m.edited_at.replace(microsecond=0).isoformat(),
                    m.author.name,
                    m.author.discriminator,
                    m.content)

    async def on_message(self, message):
        # main command for this bot is gonna be !pin
        if (message.content.startswith('!pin') or message.content.startswith('!quote')) and message.author != self.user: 
            #self.pinning.append((message.author, message.channel))
            pin_msg = await self.find_message(message.content, message.channel)
            if pin_msg is None:
                await message.channel.send("Aborting pin attempt.")
                return
            is_quote = message.content.startswith('!quote')
            if is_quote:
                start_context = await self.prompt(message.channel,
                        "!startcontext",
                        message.author,
                        "Use !startcontext to specify the message to start the pin context at.",
                        lambda m: m.created_at < pin_msg.created_at,
                        "This message was sent after the pinned message.")
                end_context = await self.prompt(message.channel,
                        "!endcontext",
                        message.author,
                        "Use !endcontext to specify the message to end the pin context at.",
                        lambda m: m.created_at > pin_msg.created_at,
                        "This message was sent before the pinned message.")
                if start_context is None or end_context is None:
                    return
            pin_string = ""
            if is_quote:
                async for m in message.channel.history(limit=40,
                        before=end_context.created_at + datetime.timedelta(microseconds=50), 
                        after=start_context.created_at - datetime.timedelta(microseconds=50)): 
                    if m == pin_msg:
                        pin_string += "==>"
                    pin_string += await self.pretty_print(m)
            else:
                pin_string = await self.pretty_print(pin_msg)
            if message.guild == None:
                filename = "pins/individual/scribe-pm-{}-{}".format(
                        message.channel.id,
                        datetime.datetime.utcnow().replace(microsecond=0).isoformat())
                big_filename = "pins/aggregate/scribe-pm-{}.txt".format(
                        message.channel.id)
            else:
                filename = "pins/individual/scribe-{}-{}-{}".format(
                        message.guild.name,
                        message.channel.name,
                        datetime.datetime.utcnow().replace(microsecond=0).isoformat())
                big_filename = "pins/aggregate/scribe-{}-{}.txt".format(
                        message.guild.name,
                        message.channel.name)
            if os.path.isfile(filename):
                filename += str(round(random.random() * 100000))
            filename += ".txt"
            with open(filename, 'a') as f:
                f.write(pin_string)
            with open(big_filename, 'a') as g:
                g.write(pin_string + "\n\n")
            await message.channel.send("Messages successfully pinned!")
            #self.pinning.remove((message.author, message.channel))
        elif message.content.startswith("!scribehelp") or message.content.startswith("!pinhelp"):
            await message.channel.send(
            "Use `!pin <first few words of message>` or `!pin <message id>` to pin a single message.\n\n" \
            "Use `!quote <first few words of message>` or `!quote <message id>` to pin a message as well as context messages around it.\n\n" \
            "Use `!startcontext` and `!endcontext` to specify the messages to start and end the pin context at.\n\n" \
            "Use `!scribehelp` or `!pinhelp` to display this help message.")

client = Scribe()
if sys.argv[1] in ("dev", "test"):
    client.run('NDE2MDUxMjQ2Nzc2OTc1MzYx.DW-1cw.Mu2snuR0kfsCnezGPcA4BoLiB7c')
elif sys.argv[1] in ("prod", "production"):
    client.run('NDEzMDgyODg0OTEyNTc4NTYw.DWTo9Q.ZW29xMylWrV5uS1qKgHPqlcVQGM')
