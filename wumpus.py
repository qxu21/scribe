from discord.ext import commands
from pymongo import MongoClient
import discord
import wumpus_config
import asyncio
import random

#TODO:
#MAKE ASYNC
#ANTIDEADNAME

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
        self.add_command(speak)

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
        await ctx.bot.db.close()
        await wumpus.logout()

# commands
@commands.command()
async def build(ctx):
	#MOVE THIS TO ONGUILDJOIN WHEN DONE
	for channel in ctx.guild.text_channels:
	#for channel in (ctx.guild.get_channel(330362198960373760),):
		if not channel.permissions_for(ctx.guild.get_member(ctx.bot.user.id)).read_messages:
			continue
		print("Working on {}.".format(channel.name))
		async for msg in channel.history(limit=None):
			print(msg.created_at.isoformat())
			l = msg.content.split()
			for m in l:
				if m == "derek":
					print("deadnames murdered++")
					m = "maya"
				elif m == "Derek":
					print("deadnames murdered++")
					m = "Maya"
			if len(l) == 0:
				#print("Contentless message.")
				continue
			user = ctx.bot.db.users.find_one({"user_id":msg.author.id})
			if user is None:
				#print("Spawning a user for {}.".format(msg.author.name))
				ctx.bot.db.users.insert_one({
					"user_id": msg.author.id,
					"total": 1,
					"bom": []
				})
			else:
				#print("Updating a user's total.")
				ctx.bot.db.users.update_one(
					{"user_id": msg.author.id},
					{"$inc": {"total": 1}}
				)
			bom_entry = ctx.bot.db.users.find_one({
				"user_id": msg.author.id,
				"bom.word": l[0]})
			if bom_entry is None:
				#print("{} has never started a message before!".format(l[0]))
				ctx.bot.db.users.update_one(
					{"user_id": msg.author.id},
					{"$addToSet": {"bom": {"word": l[0], "freq": 1}}}
				)
			else:
				#print("Bumping the count of {}".format(l[0]))
				ctx.bot.db.users.update_one(
					{
					"user_id": msg.author.id,
					"bom.word": l[0]
					},
					{"$inc": {"bom.$.freq": 1}}
				)
			for index, word in enumerate(l):
				word_entry = ctx.bot.db.words.find_one({
					"user_id": msg.author.id,
					"word": word
				})
				if word_entry is None:
					#print("{} has never been used!".format(word))
					ctx.bot.db.words.insert_one({
						"user_id": msg.author.id,
						"word": word,
						"total": 1,
						"next": [],
						"eom_count": 0
					})
				else:
					#print("Bumping {}".format(word))
					ctx.bot.db.words.update_one({
						"user_id": msg.author.id,
						"word": word
						},
						{"$inc": {"total":1}}
					)
				if index == len(l)-1:
					#print("Bumping {}'s EOM count.".format(word))
					ctx.bot.db.words.update_one({
						"user_id": msg.author.id,
						"word": word
						},
						{"$inc": {"eom_count":1}}
					)
				else:
					next_entry = ctx.bot.db.words.find_one({
						"user_id": msg.author.id,
						"word": word,
						"next.word": l[index+1]
						})
					if next_entry is None:
						#print("Adding {} to {}'s NEXT.".format(l[index+1],word))
						ctx.bot.db.words.update_one({
							"user_id": msg.author.id,
							"word": word
							},
							{"$addToSet": {"next": {"word": l[index+1], "freq": 1}}}
						)
					else:
						#print("Bumping {} in {}'s NEXT.".format(l[index+1],word))
						ctx.bot.db.words.update_one({
							"user_id": msg.author.id,
							"word": word,
							"next.word": l[index+1]
						},
						{"$inc": {"next.$.freq":1}})
	await ctx.send("Prepared the database.")

def markov_word(l, total):
	"""expects a list of {word,freq} in l"""
	print(l)
	words = []
	freqs = []
	for o in l:
		print("{};{}".format(o['word'],o['freq']))
		words.append(o['word'])
		freqs.append(o['freq']/total)
	n = random.random()
	c = 0
	for f in freqs:
		print("{}:{}".format(n,f))
		n -= f
		if n <= 0:
			break
		c += 1
	print(words[c])
	return words[c]

@commands.command()
async def speak(ctx, member : discord.Member):
	user = ctx.bot.db.users.find_one({"user_id": member.id})
	if user is None:
		await ctx.send("AAAAAAAAAA")
		return
	this_bom_word = markov_word(user['bom'],user['total'])
	#this_bom = random.choices(bom_words, weights=bom_freqs)
	msg = this_bom_word
	current_word = ctx.bot.db.words.find_one({
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
		current_word = ctx.bot.db.words.find_one({
		"user_id": member.id,
		"word": next_word
		})
	await ctx.send(msg)


loop = asyncio.get_event_loop()
loop.run_until_complete(run(wumpus_config.token))