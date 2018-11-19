import discord
from discord.ext import commands
import asyncpg
import config
import datetime
import time
import asyncio
import types
import random
import string
import os
import os.path
import sys
import re
import json

# TODO:
# 2. reactions?
# 4. pincaps
# 7. pin actual pins - ON HOLD
# allow messages that start with mentions
# add !pun
# eventually !pinfile will return urls instead of files
# add logging per documentation
# make emojis just be names, also mentions
# !aidanpinfile that does blink tags
# !babelpinfile
# unify !quote and !pinpage it
# fix \n => <br /> in webpage
# maybe !quote <user> to quote a specific user only

class Scribe(commands.Bot):
    #subclassing Bot so i can store my own properites
    #ripped from altarrel
    def __init__(self, **kwargs):
        super().__init__(
            command_prefix="!"
        )
        self.db = kwargs.pop("db")
        self.remove_command("help")
        self.add_command(pin)
        self.add_command(quote)
        self.add_command(help)
        self.add_command(pinfile)
        self.add_command(invite)
        self.add_command(omnipinfile)
        self.add_command(unpin)
        self.add_command(link)

    async def register_name(self, id, name):
        #beware! it seems old guild with default channels have identical ids between guild and default channel.
        #stay on watch for more edge cases like these
        await self.db.execute("""INSERT INTO names (id, name)
            VALUES ($1, $2)
            ON CONFLICT (id) DO UPDATE
            SET name=$2;""", id, name)

    async def on_ready(self):
        for channel in self.get_all_channels():
            if not isinstance(channel, discord.TextChannel):
                continue
            self.loop.create_task(self.register_name(channel.id, channel.name))
        for guild in self.guilds:
            pwd = ''.join([random.choice(string.ascii_letters + string.digits) for x in range(0,30)])
            await self.db.execute("""INSERT INTO guilds (id, name, pwd)
                VALUES ($1, $2, $3)
                ON CONFLICT (id) DO UPDATE
                SET name=$2, pwd=$3;""", guild.id, guild.name, pwd)
        print("on_ready complete*")

    async def on_guild_channel_create(self, channel):
        self.loop.create_task(self.register_name(channel.id, channel.name))

    async def on_guild_channel_update(self, before, after):
        self.loop.create_task(self.register_name(after.id, after.name))

    async def on_guild_join(self, guild):
        for channel in guild.text_channels:
            self.loop.create_task(self.register_name(channel.id, channel.name))
        pwd = ''.join([random.choice(string.ascii_letters + string.digits) for x in range(0,30)])
        await self.db.execute("""INSERT INTO guilds (id, name, pwd)
            VALUES ($1, $2, $3)
            ON CONFLICT (id) DO UPDATE
            SET name=$2, pwd=$3;""", guild.id, guild.name, pwd)

    #not gonna bother axing deleted channels, shouldn't be too bad

async def run(token, credentials):
    db = await asyncpg.create_pool(**credentials)

    #await db.execute("CREATE TABLE IF NOT EXISTS channels(id bigint PRIMARY KEY, userid bigint);")
    await db.execute("CREATE TABLE IF NOT EXISTS names(id bigint PRIMARY KEY, name varchar(102));")
    await db.execute("CREATE TABLE IF NOT EXISTS guilds(id bigint PRIMARY KEY, name varchar(102), pwd varchar(30));")

    scribe = Scribe(db=db)
    #scribe.loop.create_task(start_api()) #hope this works - API ON HOLD
    try:
        await scribe.start(token)
    except KeyboardInterrupt:
        await db.close()
        await scribe.logout()

async def find_message(msg, channel, count=0, silent=False, raw_string=False, after=None):
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
            search = str(search)
    # id msgs were handled above, so here we have a string that needs to be searched
    ptl_msg = await channel.history(after=after).find(
            lambda m: (m.content.startswith(search) or m.clean_content.startswith(search)) and m.channel == channel)
    #???
    #if ptl_msg is None:
    #    return None

    # we found a message
    return ptl_msg

def msg_to_json(m, isquote=False, pinner=None):
    d = {
            "id": m.id,
            "timestamp": m.created_at.replace(microsecond=0).isoformat(),
            "edited_timestamp":
                (m.edited_at.replace(microsecond=0).isoformat()
                if m.edited_at is not None else None),
            "author_name": m.author.name,
            "author_discrim": m.author.discriminator,
            "content": m.clean_content,
            "attachments": [a.url for a in m.attachments]}
    if not isquote:
        d["pinner_id"] = pinner.id if pinner is not None else None #maybe used dict.extend()
        d["pin_timestamp"] = datetime.datetime.utcnow().replace(microsecond=0).isoformat()
        d["is_quote"] = False
    return d

def pin_json(channel, j):
    # OPTIMIZATION POTENTIAL: make this async
    # ripped from pin_text and modified beyond recognition kinda
    dn = "pins/{}".format(channel.guild.id)
    fn = "{}.json".format(channel.id)
    f = os.path.join(dn,fn)
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

def format_for_feedback(s):
    # if i had figured out to chain replace calls earlier
    if s == "":
        return "[no message content]"
    s = s.replace('`','').replace('\n', ' ')
    s = s.strip()
    if len(s) <= 20:
        return s
    else:
        return s[:20] + "..."

    # this code will never execute :thinking:
    # main command for this bot is gonna be !pin
    if ctx.channel.permissions_for(ctx.guild.me).send_messages == False:
        # no send, no pin
        return

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
    #if end_context.created_at < start_context.created_at:
    # this section caused unintended behavior and is now beaned
    # rejoice
        # TOASK: abort or silently swap?
    #    tmp = end_context
    #    end_context = start_context
    #    start_context = tmp
    #pin_string = ""
    # not gonna mess with this eldritch cache
    #for m in ctx.bot._connection._messages:
    #    if (m.channel == ctx.channel
    #            and m.created_at > start_context.created_at
    #            and m.created_at < end_context.created_at):
    #        h.append(m)
    #if not (start_context in h and end_context in h):
    #    print("falling back")
    h = await ctx.channel.history(limit=200,
            before=end_context.created_at + datetime.timedelta(microseconds=1000), 
            after=start_context.created_at - datetime.timedelta(microseconds=1000)).flatten()
    ids = [m.id for m in h]
    #for m in h:
    #    print(m.content)
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

#name subject to change
@commands.command()
async def link(ctx):
    guildrow = await ctx.bot.db.fetchrow("""SELECT * 
        FROM guilds
        WHERE id=$1""", ctx.guild.id)
    await ctx.send("https://scribe.fluffybread.net/?pwd={}".format(guildrow['pwd']))


#THESE TWO FUNCTIONS HAVE BEEN COPIED INTO GLASS MOSTLY VERBATIM
#IF BIG CHANGES ARE MADE, CONSIDER MODULARIZING THESE
def json_msg_to_text(j):
    if "edited_timestamp" in j and j["edited_timestamp"] is not None:
        e = "[{} edited {}] {}#{}: {}".format(
            j["timestamp"],
            j["edited_timestamp"],
            j["author_name"],
            j["author_discrim"],
            j["content"])
    else:
        e = "[{}] {}#{}: {}".format(
            j["timestamp"],
            j["author_name"],
            j["author_discrim"],
            j["content"])
    if "attachments" in j:
        for a in j["attachments"]:
            e += "\r\nATTACHMENT: " + a
    return e.replace("\n","\r\n")

def json_file_to_string(fn):
    with open(fn) as fi:
        j = json.load(fi)
    #except json.JSONDecodeError:
    #    await ctx.send("An error occurred retrieving the pinfile.")
    #    raise
    # time to comprehend lists
    return "\r\n\r\n\r\n".join([
        re.sub(r"(\r\n){2,}", "\r\n\r\n",
            (("\r\n".join([json_msg_to_text(m) for m in e["messages"]]))
                if e["is_quote"]
                else json_msg_to_text(e)))
        for e in j])

class UnionChannelAll(commands.TextChannelConverter):
    async def convert(self, ctx, arg):
        if arg == "all":
            for c in ctx.guild.text_channels:
                if c.name == "all":
                    await ctx.send("This server has a channel named #all. If you wanted to request the serverwide pinfile, try !omnipinfile instead.")
                    return await super().convert(ctx, arg)
            return "all"
        else:
            return await super().convert(ctx, arg)

@commands.command()
async def pinfile(ctx, channel: UnionChannelAll = None):
    #if len(ctx.message.channel_mentions) == 1:
    #    cn = ctx.message.channel_mentions[0]
    #elif len(ctx.message.channel_mentions) > 1:
    #    await ctx.send("You can only ask for one channel!")
    #    return
    #else:
    #    cn = ctx.channel
    await send_pinfile(ctx, channel)

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
        fo = os.path.join(odn, "scribe-{}-{}.txt".format(
                ctx.guild.name,
                channel.name))
        if not os.path.isdir(dn) or not os.path.isfile(fi) or os.path.getsize(fi) == 0:
            await ctx.send("No pins have been recorded for this channel!")
            return
        o = json_file_to_string(fi)
    else:
        fo = os.path.join(odn, "scribe-{}.txt".format(
                ctx.guild.name))
        o = "\n\n\n".join([
            "--- #{} ---\n\n".format(
                ctx.guild.get_channel(int(os.path.splitext(f)[0])).name)
            + json_file_to_string(os.path.join(dn,f))
            for f in os.listdir(dn) if f.endswith(".json") and os.path.splitext(f)[0].isdigit()])
    with open(fo, 'w') as f:
        f.write(o)
    await ctx.send(
            file=discord.File(
                fp=fo))

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

#@commands.command()
#async def evaluate(ctx, *, arg):


loop = asyncio.get_event_loop()
loop.run_until_complete(run(config.token, config.dbc))
