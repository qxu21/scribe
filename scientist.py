import discord
from discord.ext import commands
import scientist_config
import asyncio

#BOT GOALS:
#!location to set Location topic
#!nations with a list of nations

lowner_role_id = 513965041331077120
lpart_role_id = 513965079876599808

class Scientist(commands.Bot):
    #subclassing Bot so i can store my own properites
    #ripped from altarrel
    def __init__(self, **kwargs):
        super().__init__(
            command_prefix="?"
        )
        self.is_rp = False
        self.close_rp_callback = None
        self.remove_command("help")
        self.add_command(location)
        self.add_command(invite)
        self.add_command(close)
        self.add_command(rolelist)

    async def on_message(self, msg):
        if msg.channel.id == 513959986506760202 and msg.author.id != 513989250283208714 and msg.guild.get_role(lowner_role_id).members == [] and not msg.content.startswith("?location"):
            await msg.author.send("Please use the ?location command followed by a location description before sending messages in #location.")
            await msg.delete()
            return
        elif msg.channel.id == 513959986506760202 and len(msg.guild.get_role(lowner_role_id).members) != 0 and not msg.content.startswith("?close"):
            if self.close_rp_callback is not None:
                self.close_rp_callback.cancel()
            self.close_rp_callback = self.loop.create_task(close_rp_timeout(self.get_guild(292149782619750400), self.get_channel(513959986506760202)))
        await self.process_commands(msg)

async def run(token):
    scientist = Scientist()
    try:
        await scientist.start(token)
    except KeyboardInterrupt:
        await scientist.logout()

@commands.command()
@commands.is_owner()
async def rolelist(ctx):
    await ctx.send("\n".join(["{}: {}".format(r.name,r.id) for r in ctx.guild.roles]))

@commands.command()
async def location(ctx, *, location):
    lowner_role = ctx.guild.get_role(lowner_role_id)
    if ctx.channel.id != 513959986506760202:
        await ctx.send("?location can only be used in #location.")
        return
    if len(lowner_role.members) != 0:
        await ctx.send("There is already an RP in progress. Please wait until it is closed or 10 minutes of inactivity pass.")
        return
    await ctx.author.add_roles(lowner_role,reason="?location invoked")
    await ctx.channel.edit(topic=location,reason="?location invoked")
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False, reason="?location invoked")
    await ctx.send("{} has been restricted to {}, the current RP owner. Channel description set. Please use `?invite @NATION1 @NATION2...` with pings to the nations you want to allow in the RP. As a courtesy to other nations, please use ?close to close the RP when you are done. Otherwise, your session will be ended after 10 minutes of inactivity."
        .format(ctx.channel.mention, ctx.author.mention))

def xyandz(l):
    if len(l) == 1:
        return l[0]
    elif len(l) == 2:
        return "{} and {}".format(l[0],l[1])
    else:
        m = ""
        for e in l[:-1]:
            m += e + ", "
        m += "and {}".format(l[-1])
        return m

@commands.command()
async def invite(ctx, members: commands.Greedy[discord.Member]):
    if len(members) == 0:
        await ctx.send("You must invite nations with `?invite @NATION1 @NATION2...`")
        return
    for m in members:
        await m.add_roles(ctx.guild.get_role(lpart_role_id),reason="?invite invoked")
    await ctx.send("Added {} to the RP.".format(xyandz([m.mention for m in members])))


@commands.command()
async def close(ctx):
    await close_rp(ctx.bot.get_guild(292149782619750400), ctx.bot.get_channel(513959986506760202), True)

async def close_rp_timeout(guild, channel):
    await asyncio.sleep(10)
    await close_rp(guild, channel, False)

async def close_rp(guild, channel, closed):
    if closed:
        reason = "?close invoked"
    else:
        reason = "RP timed out"
    for r in (guild.get_role(lowner_role_id),guild.get_role(lpart_role_id)):
        for m in r.members:
            await m.remove_roles(r,reason=reason)
    await channel.set_permissions(guild.default_role, send_messages=None, reason=reason)
    await channel.edit(topic="Use ?location followed by a location description to initiate an RP.",reason=reason)
    await channel.send("RP closed. Please use ?location followed by a location description to initiate a new RP. All other messages will be deleted.")


loop = asyncio.get_event_loop()
loop.run_until_complete(run(scientist_config.token))
