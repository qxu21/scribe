import discord
import datetime
import time
import asyncio
import types
import random
import os
import os.path

client = discord.Client()

async def find_message(msg, channel, count=0, silent=False, raw_string=False):
    # msg is either a string to search for *or* a message id *or* a list of words
    # *or* an int of messages to go forward/back from
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
            message = await client.get_message(channel, msg)
            if not silent:
                await client.send_message(channel,
                    "MESSAGE FOUND: The message with ID {} and contents \"{}\" corresponds to the search string."
                    .format(ptl_msg.id, ptl_msg.content))
            return message
        except discord.NotFound:
            if not silent:
                await client.send_message(channel,
                        "INVALID MESSAGE ID: Message ID not found in this channel.")
            return None
    else:
        # id msgs were handled above, so here we have a string that needs to be searched
        ptl_msg = discord.utils.find(
                lambda m: m.content.startswith(search) and m.channel == channel,
                client.messages)
        if ptl_msg is None:
            if not silent:
                await client.send_message(channel,
                        "INVALID SEARCH STRING: A message with the contents {} cannot be found in this channel."
                        .format(search))
            return None
        # we found a message
        if not silent:
            await client.send_message(channel,
                    "MESSAGE FOUND: The message with ID {} and contents \"{}\" corresponds to the search string."
                    .format(ptl_msg.id, ptl_msg.content))
        return ptl_msg

async def prompt_for_pin(channel, pinner, prompt, check=None, check_fail=""):
    await client.send_message(channel, prompt)
    while True:
        request = await client.wait_for_message(
                author=pinner,
                channel=channel,
                check=lambda m: m.content.startswith("!pin") or m.content.startswith("!stop"))
        if request.content.startswith("!stop"):
            await client.send_message(channel,
                    "Aborting pin attempt.")
            return
        msg = await find_message(request.content, channel)
        if msg is None:
            await client.send_message(channel,
                    "Please try !pinning again or abort the pin with !stop.")
            continue
        if check is not None and not check(msg):
            # check must be a function that accepts a Message and returns a boolean
            await client.send_message(channel, "MESSAGE INVALID: " + check_fail + " Please try !pinning again or abort the pin with !stop.")
            continue
        return msg

@client.event
async def on_message(message):
    # main command for this bot is gonna be !pin
    # beware i'm pretty sure the bot can trigger itself :o
    if message.content.startswith('!pin'):
        # how do we not pin the same thing twice?
        pin_msg = await find_message(message.content, message.channel)
        if pin_msg is None:
            await client.send_message(message.channel,
                    "Aborting pin attempt.")
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
        # probably a better/more pythonic/less ugly way to do this
        pin_msgs = []
        for m in client.messages:
            if m.channel == channel and m.timestamp >= start_context.timestamp and m.timestamp <= end_context.timestamp:
                # don't forget to set a max limit at some point somehwere to prevent PIN EVERYTHING scenarios
                pin_msgs.append(m)
        # this is where i :w'ed and went to bed, let's see how much momentum i lost
        # not much it seems
        # man these comments are useless but they'll provide heh later so /shrug
        pin_string = ""
        for m in pin_msgs:
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
        if m.server == None:
            filename = "scribe-pm-{}-{}".format(
                    m.channel.id,
                    time.time())
            big_filename = "scribe-pm-{}".format(
                    m.channel.id)
        else:
            filename = "scribe-{}-{}-{}".format(
                    m.server.name,
                    m.channel.name,
                    time.time())
            big_filename = "scribe-{}-{}.".format(
                    m.server.name,
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

            


#whatever the hell i want

client.run('NDEzMDgyODg0OTEyNTc4NTYw.DWTo9Q.ZW29xMylWrV5uS1qKgHPqlcVQGM')
