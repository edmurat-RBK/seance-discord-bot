from classes import EmojiConverter

import aiohttp
import asyncio
import configparser
import datetime
import discord
import discord.ext.commands
import discord.ext.tasks
from fuzzywuzzy import process, fuzz
import json
import pytz


global config
config = configparser.ConfigParser()
config.read("config.ini")

notion_headers = {
    "Authorization": f"Bearer {config['Notion']['token']}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

emoji_converter = EmojiConverter()
weather_emoji = {
    "01": ":sunny:",
    "02": ":white_sun_small_cloud:",
    "03": ":white_sun_cloud:",
    "04": ":cloud:",
    "09": ":cloud_rain:",
    "10": ":white_sun_rain_cloud:",
    "11": ":thunder_cloud_rain:",
    "13": ":cloud_snow:",
    "50": ":fog:"
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
    send_eod_message.start()


@bot.command(name="doc")
async def get_documentation(ctx, *, search):
    async with aiohttp.ClientSession() as session:
        requested_url = f"{config['Notion']['base_url']}{config['Notion']['endpoint_search']}"
        payload = {
            "query": search,
            "sort": {
                "direction":"descending",
                "timestamp":"last_edited_time"
            }
        }
        async with session.post(requested_url, json=payload, headers=notion_headers) as response:
            response_json = await response.json()
        
    output_in_file(response_json)
    
    # If 'results' is not empty: The search found something
    if response_json['results']:

        # title_list = ["".join([s['plain_text'] for s in e['properties']['title']['title']]) for e in response_json['results']]
        title_list = []
        for result in response_json['results']:
            if 'title' in result['properties']:
                title_list.append("".join([s['plain_text'] for s in result['properties']['title']['title']]))
            else:
                title_list.append(
                    next(
                        (
                            "".join(
                                [
                                    s['plain_text'] 
                                    for s in result['properties'][property]['title']
                                ]
                            )
                            for property in result['properties'] 
                            if result['properties'][property]['type'] == "title"
                        ), None
                    )
                )
        
        best_match = process.extractOne(search,title_list,scorer=fuzz.ratio)[0]
        index_best_match = title_list.index(best_match)
        
        # If the result is a page
        if response_json['results'][index_best_match]['object'] == "page":
            
            # If 'title' exists in 'properties', it's a page.
            if 'title' in response_json['results'][index_best_match]['properties']:
                embed = discord.Embed(
                    color = discord.Colour.from_str("#F9F9FA"),
                    title = response_json['results'][index_best_match]['properties']['title']['title'][0]['plain_text'],
                    description = "",
                    url = response_json['results'][index_best_match]['url'],
                    timestamp = datetime.datetime.fromisoformat(response_json['results'][index_best_match]['last_edited_time'].replace("Z",""))
                )
                if response_json['results'][index_best_match]['icon'] is not None:
                    if response_json['results'][index_best_match]['icon']['type'] == "external":
                        embed.set_thumbnail(url=response_json['results'][index_best_match]['icon']['external']['url'])
                        await ctx.send(embed=embed)
                        
                    elif response_json['results'][index_best_match]['icon']['type'] == "emoji":
                        
                        emoji_char = response_json['results'][index_best_match]['icon']['emoji']
                        png_path = emoji_converter.char_to_png(emoji_char, response_json['results'][index_best_match]['id'], config['Unicode']['save_folder'], 4)
                        png_file = discord.File(png_path, filename=png_path.split('/')[-1])
                        
                        embed.set_thumbnail(url=f"attachment://{png_path.split('/')[-1]}")
                        await ctx.send(embed=embed,file=png_file)
            
            # If 'title' don't exists in 'properties', it's a database entry.
            else:
                embed = discord.Embed(
                    color = discord.Colour.from_str("#F9F9FA"),
                    title = next((response_json['results'][index_best_match]['properties'][property]['title'][0]['plain_text'] for property in response_json['results'][index_best_match]['properties'] if response_json['results'][index_best_match]['properties'][property]['type'] == "title"), None),
                    description = "",
                    url = response_json['results'][index_best_match]['url'],
                    timestamp = datetime.datetime.fromisoformat(response_json['results'][index_best_match]['last_edited_time'].replace("Z",""))
                )
                if response_json['results'][index_best_match]['icon'] is not None:
                    if response_json['results'][index_best_match]['icon']['type'] == "file":
                        embed.set_thumbnail(url=response_json['results'][index_best_match]['icon']['file']['url'])
                for property_name in response_json['results'][index_best_match]['properties']:
                    if response_json['results'][index_best_match]['properties'][property_name]['type'] == "rich_text":
                        embed.add_field(
                            name = property_name, 
                            value = "".join([e['plain_text'] for e in response_json['results'][index_best_match]['properties'][property_name]['rich_text']]) if response_json['results'][index_best_match]['properties'][property_name]['rich_text'] else "N/A",
                            inline = False
                        )
                    elif response_json['results'][index_best_match]['properties'][property_name]['type'] == "number":
                        embed.add_field(
                            name = property_name, 
                            value = response_json['results'][index_best_match]['properties'][property_name]['number'] if response_json['results'][index_best_match]['properties'][property_name]['number'] is not None else "0",
                            inline = False
                        )
                    elif response_json['results'][index_best_match]['properties'][property_name]['type'] == "select":
                        embed.add_field(
                            name = property_name,
                            value = response_json['results'][index_best_match]['properties'][property_name]['select']['name'] if response_json['results'][index_best_match]['properties'][property_name]['select'] is not None else "N/A",
                            inline = False
                        )
                    elif response_json['results'][index_best_match]['properties'][property_name]['type'] == "multi_select":
                        embed.add_field(
                            name = property_name,
                            value = ", ".join([e['name'] for e in response_json['results'][index_best_match]['properties'][property_name]['multi_select']]) if response_json['results'][index_best_match]['properties'][property_name]['multi_select'] else "N/A",
                            inline = False
                        )
                    elif response_json['results'][index_best_match]['properties'][property_name]['type'] == "date":                        
                        embed.add_field(
                            name = property_name,
                            value = response_json['results'][index_best_match]['properties'][property_name]['date']['start'] if response_json['results'][index_best_match]['properties'][property_name]['date'] is not None else "N/A",
                            inline = False
                        )
                        
                await ctx.send(embed=embed)
        
        # If the result is a database      
        elif response_json["results"][0]['object'] == "database":
            embed = discord.Embed(
                color = discord.Colour.from_str("#F9F9FA"),
                title = response_json['results'][index_best_match]['title'][0]['plain_text'],
                description = "".join([e['plain_text'] for e in response_json['results'][index_best_match]['description']]),
                url = response_json['results'][index_best_match]['url'],
                timestamp = datetime.datetime.fromisoformat(response_json['results'][index_best_match]['last_edited_time'].replace("Z",""))
            )
            if response_json['results'][index_best_match]['cover'] is not None:
                if response_json['results'][index_best_match]['cover']['type'] == "external":
                    embed.set_thumbnail(url=response_json['results'][index_best_match]['cover']['external']['url'])
                    
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


@discord.ext.tasks.loop(time=[datetime.time(15,0,0)])
async def send_eod_message():
    # If not Friday, Saturday or Sunday, skip function
    now = datetime.datetime.now()
    if now.weekday() in [4, 5, 6]:
        return await asyncio.sleep(0)
    
    channels = []
    for channel in bot.get_all_channels():
        if config["Discord"]["channel_weather"] in channel.name:
            channels.append(bot.get_channel(channel.id))
    
    async with aiohttp.ClientSession() as session:
        requested_url = f"{config['OpenWeather']['base_url']}{config['OpenWeather']['endpoint_forecast']}".format(
            api_key = config['OpenWeather']['token']
        )
        embed = None
        async with session.get(requested_url) as response:
            if response.status == 200:
                response_json = await response.json()
                
                embed = discord.Embed(
                    color = discord.Colour.from_str("#00B5E2"),
                    title = "Demain...",
                    description = ""
                )
                
                for i in range(4,10):
                    time = datetime.datetime.fromtimestamp(response_json['list'][i]['dt'])
                    weather_icon = weather_emoji[response_json['list'][i]['weather'][0]['icon'][:-1]]
                    weather_description = response_json['list'][i]['weather'][0]['description']
                    temperature = int(round(response_json['list'][i]['main']['temp'],0))
                    feel_temperature = int(round(response_json['list'][i]['main']['feels_like'],0))
                    display_feel_temperature = (abs(response_json['list'][i]['main']['temp'] - response_json['list'][i]['main']['feels_like']) > 2)
                    temperature_icon = ":thermometer:" if temperature>0 else ":snowflake:"
                    wind_speed = int(round(response_json['list'][i]['wind']['speed'],0) * 3.6) // 5 * 5
                    wind_gust = int(round(response_json['list'][i]['wind']['gust'],0) * 3.6) // 5 * 5
                    display_wind = ((response_json['list'][i]['wind']['speed'] * 3.6 >= 30) or (response_json['list'][i]['wind']['gust']*3.6 >= 50))
                    rain_probability = int(response_json['list'][i]['pop'] * 100) // 5 * 5
                    display_rain = (response_json['list'][i]['pop'] > 0.30)
                    
                    field_value = ""
                    field_value += f"{weather_icon} {weather_description}\n{temperature_icon} {temperature}°C" 
                    if display_feel_temperature:
                        field_value += f"(ressentie: {feel_temperature}°C)"
                    field_value += "\n"
                    if display_wind:
                        field_value += f":triangular_flag_on_post: {wind_speed}km/h (rafales: {wind_gust}km/h)\n"
                    if display_rain:
                        field_value += f":droplet: {rain_probability}%\n"
                    field_value += "\n"
                        
                    embed.add_field(name=f"{time.hour}h",value=field_value,inline=True)            
                    
            else:
                embed = discord.Embed(
                    color = discord.Colour.from_str("#BE1E2E"),
                    title = "Erreur",
                    description = f"Les données météorologiques ne sont pas accessible\n*Status code: {response.status} {response.reason}*"
                )
            
        if channels:
            for channel in channels:
                await channel.send(embed=embed)




if __name__ == "__main__":
    bot.run(config["Discord"]["token"])