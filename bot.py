import aiohttp
import asyncio
import configparser
import datetime
import discord
import discord.ext.commands
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

bot = discord.ext.commands.Bot(config["Discord"]["command_prefix"], intents=intents)




def output_in_file(json_dict,file="output.json"):
    with open(file,"w") as file:
        file.write(json.dumps(json_dict))


@bot.event
async def on_ready():
    clear_retard.start()
    clear_organisation.start()


@bot.command(name="doc")
async def get_documentation(ctx, *, search):
    async with aiohttp.ClientSession() as session:
        requested_url = f"{config['Notion']['base_url']}{config['Notion']['endpoint_search']}"
        payload = {
            "query": search,
            "sort": {
                "direction":"ascending",
                "timestamp":"last_edited_time"
            }
        }
        async with session.post(requested_url, json=payload, headers=notion_headers) as response:
            response_json = await response.json()
        
    # output_in_file(response_json)
    
    # If 'results' is not empty: The search found something
    if response_json["results"]:
        
        # If the result is a page
        if response_json["results"][0]['object'] == "page":
            
            # If 'title' exists in 'properties', it's a page.
            if 'title' in response_json['results'][0]['properties']:
                embed = discord.Embed(
                    color = discord.Colour.from_str("#F9F9FA"),
                    title = response_json['results'][0]['properties']['title']['title'][0]['plain_text'],
                    description = "",
                    url = response_json['results'][0]['url'],
                    timestamp = datetime.datetime.fromisoformat(response_json['results'][0]['last_edited_time'].replace("Z",""))
                )
                if response_json['results'][0]['cover'] is not None:
                    if response_json['results'][0]['cover']['type'] == "external":
                        embed.set_thumbnail(url=response_json['results'][0]['cover']['external']['url'])
                
                await ctx.send(embed=embed)
            
            # If 'title' don't exists in 'properties', it's a database entry.
            else:
                embed = discord.Embed(
                    color = discord.Colour.from_str("#F9F9FA"),
                    title = next((response_json['results'][0]['properties'][property]['title'][0]['plain_text'] for property in response_json['results'][0]['properties'] if response_json['results'][0]['properties'][property]['type'] == "title"), None),
                    description = "",
                    url = response_json['results'][0]['url'],
                    timestamp = datetime.datetime.fromisoformat(response_json['results'][0]['last_edited_time'].replace("Z",""))
                )
                if response_json['results'][0]['icon'] is not None:
                    if response_json['results'][0]['icon']['type'] == "file":
                        embed.set_thumbnail(url=response_json['results'][0]['icon']['file']['url'])
                for property_name in response_json['results'][0]['properties']:
                    if response_json['results'][0]['properties'][property_name]['type'] == "rich_text":
                        embed.add_field(
                            name = property_name, 
                            value = "".join([e['plain_text'] for e in response_json['results'][0]['properties'][property_name]['rich_text']]),
                            inline = False
                        )
                    elif response_json['results'][0]['properties'][property_name]['type'] == "number":
                        embed.add_field(
                            name = property_name, 
                            value = response_json['results'][0]['properties'][property_name]['number'],
                            inline = False
                        )
                    elif response_json['results'][0]['properties'][property_name]['type'] == "select":
                        embed.add_field(
                            name = property_name,
                            value = response_json['results'][0]['properties'][property_name]['select']['name'],
                            inline = False
                        )
                    elif response_json['results'][0]['properties'][property_name]['type'] == "multi_select":
                        embed.add_field(
                            name = property_name,
                            value = ", ".join([e['name'] for e in response_json['results'][0]['properties'][property_name]['multi_select']]),
                            inline = False
                        )
                    elif response_json['results'][0]['properties'][property_name]['type'] == "date":
                        embed.add_field(
                            name = property_name,
                            value = response_json['results'][0]['properties'][property_name]['date']['start'],
                            inline = False
                        )
                        
                await ctx.send(embed=embed)
        
        # If the result is a database      
        elif response_json["results"][0]['object'] == "database":
            embed = discord.Embed(
                color = discord.Colour.from_str("#F9F9FA"),
                title = response_json['results'][0]['title'][0]['plain_text'],
                description = "".join([e['plain_text'] for e in response_json['results'][0]['description']]),
                url = response_json['results'][0]['url'],
                timestamp = datetime.datetime.fromisoformat(response_json['results'][0]['last_edited_time'].replace("Z",""))
            )
            if response_json['results'][0]['cover'] is not None:
                if response_json['results'][0]['cover']['type'] == "external":
                    embed.set_thumbnail(url=response_json['results'][0]['cover']['external']['url'])
                    
            await ctx.send(embed=embed)
    
    # 'results' is empty: The search has failed
    else:
        embed = discord.Embed(
            color = discord.Colour.from_str("#BE1E2E"),
            title = "Erreur",
            description = f"La page *{search}* est introuvable\nLe nom de la page recherchée est elle correcte ?"
        )
        
        await ctx.send(embed=embed)


@discord.ext.tasks.loop(time=[datetime.time(7,0,0)])
async def clear_retard():
    # On Saturdays and Sundays, skip function
    now = datetime.datetime.now()
    if now.weekday() in [5, 6]:
        return await asyncio.sleep(0)
    
    channels = []
    for channel in bot.get_all_channels():
        if config["Discord"]["channel_retard"] in channel.name:
            channels.append(bot.get_channel(channel.id))
    
    if channels:
        for channel in channels:
            await channel.purge()


@discord.ext.tasks.loop(time=[datetime.time(7,0,0)])
async def clear_organisation():
    # Skip function every day except on Mondays
    now = datetime.datetime.now()
    if now.weekday() in [1, 2, 3, 4, 5, 6]:
        return await asyncio.sleep(0)
    
    channels = []
    for channel in bot.get_all_channels():
        if config["Discord"]["channel_organisation"] in channel.name:
            channels.append(bot.get_channel(channel.id))
    
    if channels:
        for channel in channels:
            await channel.purge()




if __name__ == "__main__":
    bot.run(config["Discord"]["token"])