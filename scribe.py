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
# 4. pincaps
# 7. pin actual pins
# remove spam
# make stop slice through

# MAYBEDO:
# create its own directories

class Scribe(discord.Client):

    async def find_message(self, msg, channel, count=0, silent=False, raw_string=False):
        # msg is either a string to search for *or* a message id *or* a list of words
        # *or* an int of messages to go forward/back from UPDATE: maybe don't do this
        # was i tired when i wrote this???
        
        #what is below
        #if type(msg) == discord.Message:
        #    msg = msg.content

        if type(msg) == str and (msg.split(" ")[0] == "!pin" or msg.split(" ")[0] == "!quote"):
            # chop off !pin if it exists
            msg = msg.split(" ", 1)[1]
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
            print(search)
            ptl_msg = await channel.history().find(
                    lambda m: m.content.startswith(search) and m.channel == channel)
            #???
            #if ptl_msg is None:
            #    return None

            # we found a message
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

    def pretty_print(self, m):
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

    def pin_message(self, message):
        if type(message) == discord.Message:
            self.pin_text(message.channel, self.pretty_print(message))
        elif type(message) == list:
            for m in message:
                self.pin_text(message.channel, self.pretty_print(m)) # errors probably aaa rushhhhh

    def pin_text(self, channel, text):
        # OPTIMIZATION POTENTIAL: make this async
        # still does not support dms - channel must be GuildChannel
        # if multiple messages need ot be pinned, pass a list, since the file is opened for each call
        dn = "pins/{}".format(channel.guild.id)
        fn = "{}.txt".format(channel.id)
        if not os.path.isdir(dn):
            os.makedirs(dn)
        with open(os.path.join(dn,fn), 'a') as f:
            if type(text) == str:
                f.write(text + "\n\n")
            elif type(text) == list:
                for l in text:
                    f.write(l + "\n\n")

    """async def on_guild_join(self, guild):
        for channel in guild.text_channels:
            pinlist = []
            pin_ids = []
            pins = await channel.pins()
            for pin in pins:
                pinlist.append(self.pretty_print(pin))
                pin_ids.append(pin.id)
            self.pin_message(channel, pinlist)
            # push pickled pin_ids to database

    async def on_guild_channel_pins_update(self, channel, last_pin_time):
        # unpickle pins from database
        current_pins = await channel.pins()
        if len(previous_pins) > len(current_pins):
            # currently no unpinning functionality
            return
        # obtain the odd pin out - how?
        # self.pin_message() odd pin - maybe add self.
        """

    def format_for_feedback(self, string):
        # if i had figured out to chain replace calls earlier
        string = string.replace('`','').replace('\n', ' ')
        string = string.strip()
        if len(string) < 20:
            return string
        else:
            return string[:20] + "..."

    async def on_message(self, message):
        # main command for this bot is gonna be !pin
        if message.channel.permissions_for(message.guild.me).send_messages == False:
            # no send, no pin
            return
        if (message.content.startswith('!pin ') or message.content.startswith('!quote')) and message.author != self.user: 
            is_quote = message.content.startswith('!quote')
            if not is_quote:
                pin_msg = await self.find_message(message.content, message.channel)
                if pin_msg is None:
                    await message.channel.send("Message not found.")
                    return
            else:
                spl = message.content.split("\n")
                if len(spl) != 3:
                    await message.channel.send((
                            "Please quote in the format:\n"
                            "`!quote\n"
                            "<start message search string>\n"
                            "<end message search string>`"))
                    return
                start_context = await self.find_message(spl[1], message.channel)
                if start_context is None:
                    await message.channel.send("Start message not found.")
                    return
                end_context = await self.find_message(spl[2], message.channel)
                if end_context is None:
                    await message.channel.send("End message not found.")
                    return
                if end_context.created_at < start_context.created_at:
                    # TOASK: abort or silently swap?
                    tmp = end_context
                    end_context = start_context
                    start_context = tmp
            # this pin code will have to be migrated to a function
            pin_string = ""
            if is_quote:
                async for m in message.channel.history(limit=60,
                        before=end_context.created_at + datetime.timedelta(microseconds=1000), 
                        after=start_context.created_at - datetime.timedelta(microseconds=1000)): 
                    pin_string += self.pretty_print(m)
            else:
                pin_string = self.pretty_print(pin_msg)
            self.pin_text(message.channel, pin_string)
            if is_quote:
                await message.channel.send(
                        "The quote starting with `{}` and ending with `{}` has been pinned.".format(
                            self.format_for_feedback(start_context.content),
                            self.format_for_feedback(end_context.content)))
            else:
                await message.channel.send(
                        "The message starting with `{}` has been pinned.".format(
                            self.format_for_feedback(pin_msg.content)))
        elif message.content.startswith("!pinfile"):
            if len(message.channel_mentions) == 1:
                cn = message.channel_mentions[0]
            elif len(message.channel_mentions) > 1:
                await message.channel.send("You can only ask for one channel!")
                return
            else:
                cn = message.channel
            dn = "pins/{}".format(message.guild.id)
            fn = "{}.txt".format(cn.id)
            filename = "scribe-{}-{}-{}.txt".format(
                    message.guild.name,
                    cn.name,
                    datetime.datetime.utcnow().replace(microsecond=0).isoformat())
            if not os.path.isdir(dn) or not os.path.isfile(os.path.join(dn, fn)):
                await message.channel.send("No pins have been recorded for this channel!")
                return
            await message.channel.send(
                    file=discord.File(
                        fp=os.path.join(dn, fn),
                        filename=filename))
        elif message.content.startswith("!scribehelp") or message.content.startswith("!pinhelp"):
            await message.channel.send(
            "Use `!pin <first few words of message>` to pin a single message.\n\n" \
            "`!quote\n<first few words of start message>\n<first few words of end message>`\npins a message block.\n\n" \
            "The bot also accepts message IDs if you know how to find them.\n\n" \
            "Use `!pinfile` to grab the current channel's pin file, or `!pinfile #channel` to obtain another channel's pin file.\n\n" \
            "Use `!scribehelp` or `!pinhelp` to display this help message.\n\n" \
            "Use `!invite` to obtain an invite for Scribe.")
        elif message.content.startswith("!invite"):
            await message.channel.send("Invite Scribe to your server! https://discordapp.com/api/oauth2/authorize?client_id=413082884912578560&permissions=0&scope=bot")

client = Scribe()
if sys.argv[1] in ("dev", "test"):
    client.run('NDE2MDUxMjQ2Nzc2OTc1MzYx.DW-1cw.Mu2snuR0kfsCnezGPcA4BoLiB7c')
elif sys.argv[1] in ("prod", "production"):
    client.run('NDEzMDgyODg0OTEyNTc4NTYw.DWTo9Q.ZW29xMylWrV5uS1qKgHPqlcVQGM')
