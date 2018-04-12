import discord
import asyncio

class Censor(discord.Client):

    async def on_message(self, message):
        if message.author == self.user:
            return
        for banned_phrase in ("0w0", "ayy", "hella"):
            if message.content.find(banned_phrase) != -1:
                await message.channel.send(">" + banned_phrase)
                await message.channel.send("banned phrase")
                f = False
                for emoji in message.guild.emojis:
                    if emoji.name in ("Kalashnikov", "kalashnikov"):
                        f = True
                        await message.channel.send(str(emoji))
                if not f:
                    await message.channel.send("\U0001f52b")

client = Censor()
client.run('NDI4MzkwMDk4OTgwMDQ0ODAw.DZyY4w.Nwpbon_OxBJmZokF8iYqIF9CfoM')
