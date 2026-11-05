import os
import discord
from discord.ext import commands

# Configuração das intenções (Intents) necessárias para o bot funcionar
intents = discord.Intents.default()
intents.message_content = True

# Inicialização do bot (aqui usamos o prefixo '!', mas podes adaptar se preferires slash commands puros)
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"----------------------------------------")
    print(f"UrnaBot conectado com sucesso!")
    print(f"Logado como: {bot.user.name} (ID: {bot.user.id})")
    print(f"----------------------------------------")
    
    # Define o status do bot para dar aquela cara profissional
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name="as eleições do Dischesslord Hub"
        )
    )

# Comando simples de teste para verificar se o bot está a responder
@bot.command(name="ping")
async def ping(ctx):
    latencia = round(bot.latency * 1000)
    await ctx.send(f"🗳️ Pong! O UrnaBot está online e operando perfeitamente! Latência: `{latencia}ms`")

# Pega o token da variável de ambiente configurada na hospedagem
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("ERRO: O token do Discord não foi encontrado nas variáveis de ambiente!")
else:
    bot.run(TOKEN)
