from .text_pinfile import send_pinfile
from .utils import (
    find_message,
    create_pin,
    add_message,
    format_for_feedback,
    UnionChannelAll,
)
from discord.ext import commands
import datetime


@commands.command()
async def pin(ctx, *, search):
    message = await find_message(search, ctx.channel)
    if message is None:
        await ctx.send("Message not found.")
        return
    # pin_json(ctx.channel, msg_to_json(pin_msg, False, ctx.message.author))
    pin_id = await create_pin(ctx)
    await add_message(ctx.bot.db, message, pin_id)
    await ctx.send(
        f"The message at `{format_for_feedback(message.clean_content)}` has been pinned."
    )


@commands.command()
async def quote(ctx, *, msg):
    spl = msg.split("\n")
    if len(spl) != 2:
        await ctx.send(
            (
                "Please quote in the format:\n"
                "`!quote\n"
                "<start message search string or start message id>\n"
                "<end message search string or end message id>`"
            )
        )
        return
    start_context = await find_message(spl[0], ctx.channel)
    if start_context is None:
        await ctx.send("Start message not found.")
        return
    end_context = await find_message(
        spl[1], ctx.channel, after=start_context.created_at
    )
    if end_context is None:
        await ctx.send("End message not found.")
        return
    quoted_messages = await ctx.channel.history(
        limit=200,
        before=end_context.created_at + datetime.timedelta(microseconds=1000),
        after=start_context.created_at - datetime.timedelta(microseconds=1000),
    ).flatten()
    quoted_message_ids = [m.id for m in quoted_messages]
    if (
        start_context.id not in quoted_message_ids
        or end_context.id not in quoted_message_ids
    ):
        await ctx.send(
            "The quote selection is too large. Please limit quotes to 200 messages."
        )
        return
    pin_id = await create_pin(ctx)
    for message in quoted_messages:
        await add_message(ctx.bot.db, message, pin_id)

    await ctx.send(
        f"The quote starting at `{format_for_feedback(start_context.clean_content)}`"
        + f"and ending at `{format_for_feedback(end_context.clean_content)}` has been pinned."
    )


@commands.command()
async def unpin(ctx):
    queryval = await ctx.bot.db.fetchval(
        """
        SELECT id FROM pins
        WHERE channel=$1
        AND created_at > CURRENT_TIMESTAMP - '20 minutes'
        AND pinner=$2
        ORDER BY created_at DESC;
        """,
        ctx.channel.id,
        ctx.author.id,
    )
    if queryval is None:
        await ctx.send("Could not find a pin in this channel eligible for unpinning.")
        return
    unpinned_message_content = await ctx.bot.db.fetchval(
        """
        SELECT content FROM messages
        WHERE pin=$1
        ORDER_BY created_at;"""
    )
    # messages will be ON DELETE CASCADE'd
    await ctx.bot.db.execute(
        """
        DELETE FROM pins
        WHERE id=$1;""",
        queryval,
    )
    await ctx.send(
        f"Unpinned the pin at {format_for_feedback(unpinned_message_content)}"
    )


@commands.command()
async def link(ctx):
    guildrow = await ctx.bot.db.fetchrow(
        """SELECT *
        FROM guilds
        WHERE id=$1""",
        ctx.guild.id,
    )
    await ctx.send("https://scribe.fluffybread.net/?pwd={}".format(guildrow["pwd"]))


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


scribe_url = "https://discordapp.com/api/oauth2/authorize?client_id=413082884912578560&permissions=0&scope=bot"


@commands.command()
async def invite(ctx):
    await ctx.send(f"Invite Scribe to your server! {scribe_url}")
