import discord
import datetime
import time
import asyncio
import types
import random
import os
import os.path

# stuff to do:
# 1: finish reading migration guide nad make sure no goofs were done DONE HOPEFULLY
# 2: add a list of (user, channel) tuples to identify which user/channels are in the pinning process DONE
# 3: use channel.history() for search DONE
# 4: ???

class Scribe(discord.Client):
    pinning = []

    async def find_message(self, msg, channel, count=0, silent=False, raw_string=False):
        # msg is either a string to search for *or* a message id *or* a list of words
        # *or* an int of messages to go forward/back from
        # still in process of conversion
        if type(msg) == str and msg.split()[0] == "!pin":
            try:
                search = int(msg.split()[1])
            except ValueError:
                # chop off the !pin
                search = " ".join(msg.split()[1:])
        elif type(msg) == int:
            search = msg
        # this feels sinful
        if type(search) == int:
            try:
                message = await channel.get_message(msg)
                if not silent:
                    await channel.send(
                        "MESSAGE FOUND: The message with ID {} and contents \"{}\" corresponds to the search string."
                        .format(ptl_msg.id, ptl_msg.content))
                return message
            except discord.NotFound:
                if not silent:
                    await channel.send("INVALID MESSAGE ID: Message ID not found in this channel.")
                return None
        else:
            # id msgs were handled above, so here we have a string that needs to be searched
            ptl_msg = discord.utils.find(
                    lambda m: m.content.startswith(search) and m.channel == channel,
                    client.messages)
            if ptl_msg is None:
                if not silent:
                    await channel.send(,
                            "INVALID SEARCH STRING: A message with the contents {} cannot be found in this channel."
                            .format(search))
                return None
            # we found a message
            if not silent:
                await channel.send(,
                        "MESSAGE FOUND: The message with ID {} and contents \"{}\" corresponds to the search string."
                        .format(ptl_msg.id, ptl_msg.content))
            return ptl_msg

    async def prompt_for_pin(self, channel, pinner, prompt, check=None, check_fail=""):
        await channel.send(prompt)
        while True:
            request = await client.wait_for(
                    'message',
                    check=lambda m: m.author == pinner and m.channel == channel and (m.content.startswith("!pin") or m.content.startswith("!stop")))
            if request.content.startswith("!stop"):
                await channel.send("Aborting pin attempt.")
                return
            elif request.content.startswith("!nocontext"):
                await channel.send("Pinning message without context.")
            msg = await find_message(request.content, channel)
            if msg is None:
                await channel.send("Please try !pinning again or abort the pin with !stop.")
                continue
            if check is not None and not check(msg):
                # check must be a function that accepts a Message and returns a boolean
                await channel.send("MESSAGE INVALID: " + check_fail + " Please try !pinning again or abort the pin with !stop.")
                continue
            return msg

    async def on_message(self, message):
        # main command for this bot is gonna be !pin
        if message.content.startswith('!pin') and message.author != self.user and (message.author, message.channel) not in self.pinning:
            self.pinning.append((message.author, message.channel))
            pin_msg = await find_message(message.content, message.channel)
            if pin_msg is None:
                await message.channel.send("Aborting pin attempt.")
                return
            start_context = await prompt_for_pin(message.channel,
                    message.author,
                    "What message would you like to begin the pin context at?",
                    lambda m: m.timestamp < pin_msg.timestamp,
                    "This message was sent after the pinned message.")
            end_context = await prompt_for_pin(message.channel,
                    message.author,
                    "What message would you like to end the pin context at?",
                    lambda m: m.timestamp > pin_msg.timestamp,
                    "This message was sent before the pinned message.")
            # time to begin the message trawl of hell
            # hey look 1.0 made this nice
            pin_string = ""
            async for m in message.channel.history(limit=40, before=start_context, after=end_context):
                # use datetime.isoformat()
                if m.edited_timestamp is None:
                    pin_string += "[{}] {}#{}: {}\n".format(
                            m.timestamp.isoformat(timespec='seconds'),
                            m.author.name,
                            m.author.discriminator,
                            m.content)
                else:
                    pin_string += "[{} edited {}] {}#{}: {}\n".format(
                            m.timestamp.isoformat(timespec='seconds'),
                            m.edited_timestamp.isoformat(timespec='seconds'),
                            m.author.name,
                            m.author.discriminator,
                            m.content)
            if m.guild == None:
                filename = "scribe-pm-{}-{}".format(
                        m.channel.id,
                        time.time())
                big_filename = "scribe-pm-{}".format(
                        m.channel.id)
            else:
                filename = "scribe-{}-{}-{}".format(
                        m.guild.name,
                        m.channel.name,
                        time.time())
                big_filename = "scribe-{}-{}.".format(
                        m.guild.name,
                        m.channel.name)
            if not os.path.isfile(filename):
                filename += ".txt"
                f = open(filename, 'w')
            else:
                filename += str(round(random.random() * 100000)) + ".txt"
                f = open(filename, 'w')
            if not os.path.isfile(big_filename):
                big_filename += ".txt"
                g = open(big_filename, 'w')
            else:
                g = open(big_filename, 'a')
            f.write(pin_string)
            f.close()
            g.write("\n\n" + pin_string)
            g.close()

client = Scribe()
client.run('NDEzMDgyODg0OTEyNTc4NTYw.DWTo9Q.ZW29xMylWrV5uS1qKgHPqlcVQGM')
