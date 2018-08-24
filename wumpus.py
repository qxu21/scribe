from discord.ext import commands
from pymongo import MongoClient
import discord
import wumpus_config
import asyncio

class Wumpus(commands.Bot):
    #subclassing Bot so i can store my own properites
    #ripped from altarrel
    def __init__(self, **kwargs):
        super().__init__(
            command_prefix="wumpus "
        )
        self.db_client = MongoClient()
        self.db = self.db_client.wumpus
        self.remove_command("help")
        self.add_command(build)

    async def on_ready(self):
        # maybe do things
        pass

    async def on_guild_join(self, guild):
        # maybe do things
        pass

    #not gonna bother axing deleted channels, shouldn't be too bad

async def run(token):
    wumpus = Wumpus()
    try:
        await wumpus.start(token)
    except KeyboardInterrupt:
        await db.close()
        await wumpus.logout()

# commands
@commands.command()
async def build(ctx):
	#MOVE THIS TO ONGUILDJOIN WHEN DONE
	entry = {
		"guild_id": ctx.guild.id,
		"members": {}
	}
	ctx.bot.db.guilds.insert_one(entry)
	entry = {
		"member_id": member.id,
		"bom": {}
	}
	entry["words"] = {}
	for channel in ctx.guild.channels():
		async for msg in channel.history(limit=100):
			if 
			l = msg.content.split()
			if l[0] not in entry["bom"]:
				entry["bom"][l[0]] = 0
			entry["bom"][l[0]] += 1
			for index, word in enumerate(l):
				if word not in entry["words"]:
					entry["words"][word] = {
						"word": word,
						"total": 0,
						"next": {},
						"eom_count": 0
					}
				entry["words"][word]["total"] += 1
				if index == len(l)-1:
					entry["words"][word]["eom_count"] += 1
				else:
					if l[index+1] not in entry["words"][word]["next"]:
						entry["words"][word]["next"][l[index+1]] = 0
					#this_next = (d for d in entry["words"][word]["next"] if d['word'] == l[index+1])[0]
					entry["words"][word]["next"][l[index+1]] += 1
	
	await ctx.send("Prepared the database for {}.".format(member.mention))

loop = asyncio.get_event_loop()
loop.run_until_complete(run(wumpus_config.token))