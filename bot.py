import discord
from discord.ext import commands
from datetime import datetime
from config import TOKEN, SERVICE_CHANNEL_ID, RAPPORT_CHANNEL_ID
import asyncio

# Configuration du bot
prefix = "!"  # Préfixe des commandes du bot

intents = discord.Intents.default()
intents.reactions = True
intents.message_content = True

bot = commands.Bot(command_prefix=prefix, intents=intents)

pointeuse = {}
total_agents_en_service = 0

def strfdelta(timedelta):
    hours, remainder = divmod(timedelta.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}"

@bot.event
async def on_ready():
    global total_agents_en_service
    total_agents_en_service = 0
    for guild in bot.guilds:
        channel = guild.get_channel(SERVICE_CHANNEL_ID)
        if channel:
            message = await channel.send("Cliquez sur ✅ pour prendre son service et ❌ pour terminer son service.")
            await message.add_reaction("✅")
            await message.add_reaction("❌")
            total_agents_en_service += len(pointeuse)
    
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name=f"{total_agents_en_service} agent(s) en service"
    )
    await bot.change_presence(activity=activity)
    print("Bot connecté !")

async def send_rapport():
    today = datetime.now().date()

    rapport_embed = discord.Embed(title="Rapport des pointages", color=0x00ff00)

    for user_id, data in pointeuse.items():
        user = await bot.fetch_user(user_id)
        heure_prise_service = data["heure_prise_service"]
        heure_fin_service = data["heure_fin_service"]

        if heure_prise_service.date() == today:
            rapport_embed.add_field(name="👮 Agent", value=data["member"].display_name)
            rapport_embed.add_field(name="📥 10-8", value=heure_prise_service.strftime('%H:%M'), inline=False)

            if heure_fin_service:
                rapport_embed.add_field(name="📤 10-10", value=heure_fin_service.strftime('%H:%M'), inline=False)
                temps_pointe = heure_fin_service - heure_prise_service
                rapport_embed.add_field(name="⌛ Service", value=strfdelta(temps_pointe), inline=False)
            else:
                rapport_embed.add_field(name="En service", value="\u200b", inline=False)

    rapport_channel = bot.get_channel(RAPPORT_CHANNEL_ID)
    await rapport_channel.send(embed=rapport_embed)

@bot.event
async def on_reaction_add(reaction, user):
    if not user.bot:
        global total_agents_en_service
        channel = reaction.message.channel
        if channel.id == SERVICE_CHANNEL_ID:
            if user.id not in pointeuse and reaction.emoji == "✅":
                member = await reaction.message.guild.fetch_member(user.id)
                pointeuse[user.id] = {
                    "member": member,
                    "heure_prise_service": datetime.now(),
                    "heure_fin_service": None,
                    "message": None  # Store the message object for removal
                }
                await reaction.message.remove_reaction("❌", user)
                message = await reaction.message.channel.send(f"{user.mention} a pris son service.")
                pointeuse[user.id]["message"] = message  # Store the message object
                total_agents_en_service += 1
                await asyncio.sleep(1)  # Wait for 1 minute
                await message.delete()  # Delete the message
                pointeuse[user.id]["message"] = None  # Clear the message object
            elif user.id in pointeuse and reaction.emoji == "❌":
                heure_fin_service = datetime.now()
                pointeuse[user.id]["heure_fin_service"] = heure_fin_service
                await reaction.message.remove_reaction("✅", user)
                message = await reaction.message.channel.send(f"{user.mention} a terminé son service.")
                total_agents_en_service -= 1
                if total_agents_en_service < 0:  # Ensure the total does not become negative
                    total_agents_en_service = 0
                await send_rapport()  # Send the report immediately after ending service
                await asyncio.sleep(1)  # Wait for 1 minute
                await message.delete()  # Delete the message
            elif user.id in pointeuse and reaction.emoji == "✅":
                del pointeuse[user.id]  # Remove the existing entry
                member = await reaction.message.guild.fetch_member(user.id)
                pointeuse[user.id] = {
                    "member": member,
                    "heure_prise_service": datetime.now(),
                    "heure_fin_service": None,
                    "message": None  # Store the message object for removal
                }
                await reaction.message.remove_reaction("❌", user)
                message = await reaction.message.channel.send(f"{user.mention} a repris son service.")
                total_agents_en_service += 1
                await send_rapport()  # Send the report immediately after taking service again
                await asyncio.sleep(1)  # Wait for 1 minute
                await message.delete()  # Delete the message
                pointeuse[user.id]["message"] = None  # Clear the message object

            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{total_agents_en_service} agent(s) en service"
            )
            await bot.change_presence(activity=activity)


@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx):
    channel = ctx.channel
    await channel.purge()


bot.run(TOKEN)
