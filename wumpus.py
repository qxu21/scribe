from discord.ext import commands
#from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
import discord
import wumpus_config
import asyncio
import random

#TODO:
#MAYBE REGEN BORING PHRASES
#DB IDENTIFIED AS BOTTLENECK

class Wumpus(commands.Bot):
    #subclassing Bot so i can store my own properites
    #ripped from altarrel
    def __init__(self, **kwargs):
        super().__init__(
            command_prefix="w"
        )
        self.db_client = AsyncIOMotorClient()
        self.db = self.db_client.wumpus
        self.remove_command("help")
        self.add_command(build)
        self.add_command(speak)

    #async def on_ready(self):
        # maybe do things
    #    pass

    #async def on_guild_join(self, guild):
        # maybe do things
    #    pass

    #not gonna bother axing deleted channels, shouldn't be too bad

async def run(token):
    wumpus = Wumpus()
    try:
        await wumpus.start(token)
    except KeyboardInterrupt:
        await ctx.bot.db.close()
        await wumpus.logout()

# commands
@commands.command()
@commands.is_owner()
async def build(ctx):
	#MOVE THIS TO ONGUILDJOIN WHEN DONE
	#important: each member doesn't need guildid in the mem db, but does need it attached in mongo
	#the mem db will be denormalized (embedded) to decrease in-memory footprint of the db
	#while the mongo db is normalized (flattened) so as little disk data is read as possible
	mem_db = {}
	for channel in ctx.guild.text_channels:
		if not channel.permissions_for(ctx.guild.get_member(ctx.bot.user.id)).read_messages:
			continue
		print("Working on {}.".format(channel.name))
		async for msg in channel.history(limit=None):
			print(msg.created_at.isoformat())
			user_id = msg.author.id
			l = msg.clean_content.replace("derek","maya").replace("Derek","Maya").split()
			if len(l) == 0:
				continue
			if user_id not in mem_db:
				mem_db[user_id] = {
					"total": 1,
					"bom": {},
					"words": {}
				}
			else:
				mem_db[user_id]["total"] += 1
			if l[0] not in mem_db[user_id][bom]:
				mem_db[user_id]["bom"][l[0]] = 1
			else:
				mem_db[user_id]["bom"][l[0]] += 1
			for index, word in enumerate(l):
				if word not in mem_db[user_id]["words"]:
					mem_db[user_id]["words"][word] = {
						"total": 1,
						"next": {},
						"eom_count": 0
					}
				else:
					mem_db[user_id]["words"][word]["total"] += 1
				if index == len(l)-1:
					mem_db[user_id]["words"][word]["eom_count"] += 1
				else:
					if l[index+1] not in mem_db[user_id]["words"][word]["next"]:
						mem_db[user_id]["words"][word]["next"][l[index+1]] = 1
					else:
						mem_db[user_id]["words"][word]["next"][l[index+1]] += 1
	for user in mem_db:
		ctx.bot.db.users.insert_one({
			
			})
	await ctx.send("Prepared the database.")

def markov_word(l, total):
	"""expects a list of {word,freq} in l"""
	#print(l)
	words = []
	freqs = []
	for o in l:
		#print("{};{}".format(o['word'],o['freq']))
		words.append(o['word'])
		freqs.append(o['freq']/total)
	n = random.random()
	c = 0
	for f in freqs:
		#print("{}:{}".format(n,f))
		n -= f
		if n <= 0:
			break
		c += 1
	#print(words[c])
	return words[c]

@commands.command()
async def speak(ctx, member : discord.Member):
	user = await ctx.bot.db.users.find_one({"user_id": member.id})
	if user is None:
		await ctx.send("AAAAAAAAAA")
		return
	this_bom_word = markov_word(user['bom'],user['total'])
	#this_bom = random.choices(bom_words, weights=bom_freqs)
	msg = this_bom_word
	current_word = await ctx.bot.db.words.find_one({
		"user_id": member.id,
		"word": this_bom_word
		})
	while True:
		#next_words = [None]
		#next_freqs = [current_word['eom_count']]
		#for c in current_word['next']:
		#	next_words.append(c['word'])
		#	next_freqs.append(c['freq'])
		#current_word = random.choices(next_words, next_freqs)
		if current_word['eom_count'] > 0:
			current_word['next'].append({'word': None, 'freq': current_word['eom_count']})
		next_word = markov_word(current_word['next'],current_word['total'])
		if next_word is None:
			break
		msg += " " + next_word
		current_word = await ctx.bot.db.words.find_one({
		"user_id": member.id,
		"word": next_word
		})
	await ctx.send(msg)


loop = asyncio.get_event_loop()
loop.run_until_complete(run(wumpus_config.token))