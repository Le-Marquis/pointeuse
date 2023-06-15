import discord
from discord.ext import commands
from datetime import datetime
import asyncio
from config import TOKEN

# Configuration du bot
prefix = "!"  # Préfixe des commandes du bot

intents = discord.Intents.default()
intents.reactions = True
intents.message_content = True

bot = commands.Bot(command_prefix=prefix, intents=intents)

pointeuse = {}
total_agents_en_service = 0

service_channel_id = None
rapport_channel_id = None


def strfdelta(timedelta):
    hours, remainder = divmod(timedelta.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}"


@bot.event
async def on_ready():
    global total_agents_en_service
    total_agents_en_service = 0
    for guild in bot.guilds:
        channel = guild.get_channel(service_channel_id)
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


@bot.event
async def on_reaction_add(reaction, user):
    if not user.bot:
        global total_agents_en_service
        channel = reaction.message.channel
        if channel.id == service_channel_id:
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
                await asyncio.sleep(30)  # Wait for 1 minute
                await message.delete()  # Delete the message
                pointeuse[user.id]["message"] = None  # Clear the message object
            elif user.id in pointeuse and reaction.emoji == "❌":
                heure_fin_service = datetime.now()
                pointeuse[user.id]["heure_fin_service"] = heure_fin_service
                await reaction.message.remove_reaction("✅", user)
                message = await reaction.message.channel.send(f"{user.mention} a terminé son service.")
                total_agents_en_service -= 1
                await asyncio.sleep(30)  # Wait for 1 minute
                await message.delete()  # Delete the message
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{total_agents_en_service} agent(s) en service"
            )
            await bot.change_presence(activity=activity)


@bot.command()
async def setrapport(ctx):
    global rapport_channel_id
    rapport_channel_id = ctx.channel.id
    await ctx.message.delete()
    message = await ctx.send(f"Le salon de rapport a été défini sur <#{rapport_channel_id}>.")
    await asyncio.sleep(5)  # Attendre 5 secondes
    await message.delete()


@bot.command()
async def setpointeuse(ctx):
    global service_channel_id
    service_channel_id = ctx.channel.id
    await ctx.message.delete()
    message = await ctx.send(f"Le salon pointeuse a été défini sur <#{service_channel_id}>.")
    await asyncio.sleep(5)  # Attendre 5 secondes
    await message.delete()
    await on_ready()



@bot.command()
async def rapport(ctx):
    rapport_message = "Rapport des pointages :\n\n"
    today = datetime.now().date()
    
    for user_id, data in pointeuse.items():
        user = await bot.fetch_user(user_id)
        heure_prise_service = data["heure_prise_service"]
        heure_fin_service = data["heure_fin_service"]
        
        if heure_prise_service.date() == today:
            rapport_message += f"👮 Agent : {data['member'].display_name}\n"
            rapport_message += f"📥 Heure de prise de service : {heure_prise_service.strftime('%H:%M')}\n"
            
            if heure_fin_service:
                rapport_message += f"📤 Heure de fin de service : {heure_fin_service.strftime('%H:%M')}\n"
                temps_pointe = heure_fin_service - heure_prise_service
                rapport_message += f"⌛ Durée de service : {strfdelta(temps_pointe)}\n"
            else:
                rapport_message += "En service\n"
                
            rapport_message += "\n"
    
    rapport_channel = bot.get_channel(rapport_channel_id)
    await rapport_channel.send(rapport_message)


bot.run(TOKEN)
