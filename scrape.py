import discord
import json
import datetime

after_year = None
after_month = None
after_day = None
token = None

client = discord.Client()

@client.event
async def on_ready():
	channel = client.get_channel(214791280394240001)
	msgs = []
	async for msg in channel.history(after=datetime.datetime(year=after_year,month=after_month,day=after_day)):
		print(msg.created_at.isoformat())
		msgs.append({"user_id":msg.author.id,"guild_id":msg.guild.id,"content":msg.clean_content})
	with open("dump.json","w") as f:
		json.dump(msgs, f)

client.run(token)