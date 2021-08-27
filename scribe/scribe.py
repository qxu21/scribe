import discord
from discord.ext import commands
import asyncpg
import config
import asyncio
import random
import string
from .commands import pin, quote, help, pinfile, invite, omnipinfile, unpin, link

# TODO:
# 2. reactions?
# 4. pincaps
# 7. pin actual pins - ON HOLD
# allow messages that start with mentions
# add !pun
# add logging per documentation
# make emojis just be names, also mentions
# !aidanpinfile that does blink tags
# !babelpinfile
# unify !quote and !pinpage it
# fix \n => <br /> in webpage
# maybe !quote <user> to quote a specific user only


class Scribe(commands.Bot):
    # subclassing Bot so i can store my own properites
    # ripped from altarrel
    def __init__(self, **kwargs):
        super().__init__(command_prefix="!")
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
        # beware! it seems old guild with default channels have identical ids between guild and default channel.
        # stay on watch for more edge cases like these
        await self.db.execute(
            """INSERT INTO names (id, name)
            VALUES ($1, $2)
            ON CONFLICT (id) DO UPDATE
            SET name=$2;""",
            id,
            name,
        )

    async def on_ready(self):
        for channel in self.get_all_channels():
            if not isinstance(channel, discord.TextChannel):
                continue
            self.loop.create_task(self.register_name(channel.id, channel.name))
        for guild in self.guilds:
            pwd = "".join(
                [
                    random.choice(string.ascii_letters + string.digits)
                    for x in range(0, 30)
                ]
            )
            await self.db.execute(
                """INSERT INTO guilds (id, name, pwd)
                VALUES ($1, $2, $3)
                ON CONFLICT (id) DO UPDATE
                SET name=$2, pwd=$3;""",
                guild.id,
                guild.name,
                pwd,
            )
        print("on_ready complete*")

    async def on_guild_channel_create(self, channel):
        self.loop.create_task(self.register_name(channel.id, channel.name))

    async def on_guild_channel_update(self, before, after):
        self.loop.create_task(self.register_name(after.id, after.name))

    async def on_guild_join(self, guild):
        for channel in guild.text_channels:
            self.loop.create_task(self.register_name(channel.id, channel.name))
        pwd = "".join(
            [random.choice(string.ascii_letters + string.digits) for x in range(0, 30)]
        )
        await self.db.execute(
            """INSERT INTO guilds (id, name, pwd)
            VALUES ($1, $2, $3)
            ON CONFLICT (id) DO UPDATE
            SET name=$2, pwd=$3;""",
            guild.id,
            guild.name,
            pwd,
        )

    # not gonna bother axing deleted channels, shouldn't be too bad


async def run(token, credentials):
    db = await asyncpg.create_pool(**credentials)

    # autoincrementing ID for PINS
    await db.execute(
        """CREATE TABLE IF NOT EXISTS names(
            id bigint PRIMARY KEY,
            name varchar(102));"""
    )
    await db.execute(
        """CREATE TABLE IF NOT EXISTS guilds(
            id bigint PRIMARY KEY,
            name varchar(102),
            pwd varchar(30));"""
    )
    # dates - YYYY-MM-DDTHH:MM:SS
    # precision 0 - no fractional seconds
    await db.execute(
        """CREATE TABLE IF NOT EXISTS pins(
            id integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            guild bigint,
            channel bigint,
            created_at timestamp(0) WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            pinner bigint);
            """
    )
    await db.execute(
        """CREATE TABLE IF NOT EXISTS messages(
            id bigint PRIMARY KEY,
            author bigint,
            created_at timestamp(0) without time zone,
            edited_at timestamp(0) without time zone,
            content text,
            reply bigint REFERENCES messages,
            pin integer REFERENCES pins);"""
    )
    # TODO: possible attachment url table?

    scribe = Scribe(db=db)
    # scribe.loop.create_task(start_api()) #hope this works - API ON HOLD
    try:
        await scribe.start(token)
    except KeyboardInterrupt:
        await db.close()
        await scribe.logout()


def start_scribe():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(config.token, config.dbc))
