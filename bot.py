import aiohttp
import configparser
import discord
from discord.ext.commands import Bot
import discord.ext.tasks
import json


global config
config = configparser.ConfigParser()
config.read("config.ini")

notion_headers = {
    "Authorization": f"Bearer {config['Notion']['token']}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

intents=discord.Intents.default()
intents.message_content = True

bot = Bot(config["Discord"]["command_prefix"], intents=intents)

@bot.command(name="doc")
async def get_page_list(ctx, *search):
    str_search = " ".join([*search])
    async with aiohttp.ClientSession() as session:
        requested_url = f"{config['Notion']['base_url']}{config['Notion']['endpoint_search']}"
        payload = {
            "query": str_search,
            "sort": {
                "direction":"ascending",
                "timestamp":"last_edited_time"
            }
        }
        async with session.post(requested_url, json=payload, headers=notion_headers) as response:
            json = await response.json()
            if json["results"]:
                output_message = f"**{json['results'][0]['properties']['title']['title'][0]['plain_text']}**\n{json['results'][0]['url']}\n\n*Derniere modification: {json['results'][0]['last_edited_time']}*"
            else:
                output_message = f"Impossible de trouver la page *{str_search}*"
    await ctx.send(output_message)

bot.run(config["Discord"]["token"])