from discord.ext import commands
#from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
import discord
import wumpus_config
import asyncio
import random
import psutil

TOTAL_MEMORY = 1025130496 #in bytes

#TODO:
#MAYBE REGEN BORING PHRASES
#DB IDENTIFIED AS BOTTLENECK
#ADD NEW MESSAGES TO DB

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
	guild_id = ctx.guild.id
	for channel in ctx.guild.text_channels:
		if not channel.permissions_for(ctx.guild.get_member(ctx.bot.user.id)).read_messages:
			continue
		print("Working on {}.".format(channel.name))
		counter_until_mem_check = 10
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
			counter_until_mem_check -= 1
			if counter_until_mem_check <= 0:
				this_process = psutil.Process(os.getpid())
				if process.memory_info()[0] >= TOTAL_MEMORY * (1/2):
					await dump_db(ctx.bot.db,mem_db,ctx.guild.id)
				counter_until_mem_check = 10


async def dump_db(db,mem_db,guild_id):
	for user_id, user in mem_db.items():
		#await db.users.insert_one({
		#	"user_id": user_id,
		#	"guild_id": ctx.guild.id,
		#	"total": 1,
		#	"bom": bom_array
		#})
		db_user = await db.users.find_one({"user_id":user_id})
		if db_user is None:
			bom_array = [{
				"word": bom_word,
				"freq": bom_freq
			} for bom_word, bom_freq in user["bom"].items()]
			await db.users.insert_one({
				"user_id": user_id,
				"guild_id": guild_id,
				"total": user["total"],
				"bom": bom_array
			})
		else:
			#db_bom = db_user["bom"]
			#for bom_word, bom_freq in user["bom"].items():
			#	if bom_word in db_bom:
			#		db_bom[bom_word] += bom_freq
			#	else:
			#		db_bom[bom_word] = bom_freq
			#await db.users.update_one(
			#	{
			#	"user_id": msg.author.id,
			#	"guild_id": msg.guild.id
			#	},
			#	{"$set": {"bom":db_bom}}
			#)
			# so i was going to do this by iterating over the user bom
			# but i realized that's an O(n) lookup for every word in the bom table,
			# since i have to walk through it over and over.
			# therefore, i'm doing the two-step solution, and this shouldn't be too bad with
			# a db that grows in O(log n) time:
			# 1. walk throught the db's BOM array and increment and remove all words
			# 2. push new words to the db
			db_bom = db_user["bom"]
			# update all existing values, iterating over the disk values
			for db_bom_obj in db_bom:
				if db_bom_obj["word"] in user["bom"]:
					db_bom_obj["freq"] += user["bom"][db_bom_obj["word"]]
					del user["bom"][db_bom_obj["word"]]
			#push all the new values
			db_bom.extend([{
				"word": bom_word,
				"freq": bom_freq
			} for bom_word, bom_freq in user["bom"].items()])
			await db.users.update_one({
				"user_id": user_id,
				"guild_id": guild_id,
				},
				{
				"$set": {"bom":db_bom}, #i think taking the BOM out, manipulating in memory, and putting back is the best idea
				"$inc": {"total":user["total"]}
				})
		del user["bom"] #gotta free that memory
		#however, the words are going to be dealt with by the user dict
		for word_word, word_obj in user["words"].items():
			word_entry = await db.words.find_one({
				"user_id": user_id,
				"guild_id": guild_id,
				"word": word
			})
			if word_entry is None:
				await db.words.insert_one({
					"user_id": user_id,
					"guild_id": guild_id,
					"word": word_word,
					"total": word_obj["total"],
					"next": [{"word":w,"freq":f} for w,f in word_obj["next"].items()],
					"eom_count": word_obj["eom_count"]
				})
			else:
				#copypasting algorithm, heck this
				db_next = word_entry["next"]
				# update all existing values, iterating over the disk values
				for db_next_obj in db_next:
					if db_next_obj["word"] in word_obj["next"]:
						db_next_obj["freq"] += word_obj["next"][db_next_obj["word"]]
						del word_obj["next"][db_next_obj["word"]]
				#push all the new values
				db_next.extend([{
					"word": next_word,
					"freq": next_freq
				} for next_word, next_freq in word_obj["next"].items()])
				#update total at end
				await db.words.update_one({
					"user_id": user_id,
					"guild_id": guild_id,
					"word": word_word
					},
					{
					"$set": {"next":db_next}
					"$inc": {"total":word_obj["total"],"eom_count":word_obj["eom_count"]},
					}
				)

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