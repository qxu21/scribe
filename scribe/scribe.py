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
            """INSERT INTO channels (id, name)
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
                    for _ in range(0, 30)
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

    await db.execute(
        """
        DROP TABLE IF EXISTS channels CASCADE;
        DROP TABLE IF EXISTS guilds CASCADE;
        DROP TABLE IF EXISTS pins CASCADE;
        DROP TABLE IF EXISTS messages CASCADE;
        DROP TABLE IF EXISTS messages_pins CASCADE;
        DROP TABLE IF EXISTS attachments CASCADE;"""
    )

    # autoincrementing ID for PINS
    await db.execute(
        """CREATE TABLE IF NOT EXISTS channels(
            id BIGINT PRIMARY KEY,
            guild BIGINT,
            name VARCHAR(102));"""
    )
    await db.execute(
        """CREATE TABLE IF NOT EXISTS guilds(
            id BIGINT PRIMARY KEY,
            name VARCHAR(102),
            pwd VARCHAR(30));"""
    )
    # dates - YYYY-MM-DDTHH:MM:SS
    # precision 0 - no fractional seconds
    # possibly is_single
    await db.execute(
        """CREATE TABLE IF NOT EXISTS pins(
            id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            guild BIGINT,
            channel BIGINT,
            created_at TIMESTAMP(0) WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            pinner BIGINT);
            """
    )
    await db.execute(
        """CREATE TABLE IF NOT EXISTS messages(
            id BIGINT PRIMARY KEY,
            author BIGINT,
            created_at TIMESTAMP(0) WITHOUT TIME ZONE,
            edited_at TIMESTAMP(0) WITHOUT TIME ZONE,
            content TEXT,
            url TEXT,
            reply BIGINT REFERENCES messages ON DELETE RESTRICT);"""
    )

    # TODO: maybe rename is_reply

    await db.execute(
        """CREATE TABLE IF NOT EXISTS messages_pins(
            message BIGINT REFERENCES messages ON DELETE CASCADE,
            pin INTEGER REFERENCES pins ON DELETE CASCADE,
            is_reply BOOL);"""
    )
    await db.execute(
        """CREATE TABLE IF NOT EXISTS attachments(
            message BIGINT REFERENCES messages ON DELETE CASCADE,
            url TEXT);"""
    )

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
