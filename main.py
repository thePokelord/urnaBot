import os
import random
import discord
from discord.ext import commands
from discord import app_commands, ui
from supabase import create_client, Client

# Configuração de Intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Conexão com o Supabase (puxa das Variáveis de Ambiente da FadeHost)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNÇÕES DO BANCO DE DADOS (CHESSCOINS) ---

def obter_chesscoins(user_id: int) -> int:
    try:
        res = supabase.table("chesscoins").select("saldo").eq("user_id", str(user_id)).execute()
        if res.data:
            return res.data[0]["saldo"]
        return 0
    except Exception as e:
        print(f"Erro ao ler saldo: {e}")
        return 0

def adicionar_chesscoins(user_id: int, quantia: int):
    if quantia <= 0:
        return
    saldo_atual = obter_chesscoins(user_id)
    novo_saldo = saldo_atual + quantia
    try:
        supabase.table("chesscoins").upsert(
            {"user_id": str(user_id), "saldo": novo_saldo}
        ).execute()
    except Exception as e:
        print(f"Erro ao salvar saldo no Supabase: {e}")

# --- EVENTOS E COMANDOS DO URNABOT ---

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"UrnaBot online como {bot.user}!")

# Modal para criar sorteio
class SorteioModal(ui.Modal, title="Criar Sorteio de Chesscoins"):
    titulo = ui.TextInput(label="Título do Sorteio", placeholder="Ex: Sorteio de 500 Chesscoins!")
    premio = ui.TextInput(label="Valor do Prêmio (Chesscoins)", placeholder="100", default="100")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            valor = int(self.premio.value)
        except ValueError:
            await interaction.response.send_message("O valor do prêmio precisa ser um número inteiro!", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"🎉 {self.titulo.value}",
            description=f"**Prêmio:** {valor} 🪙 Chesscoins\nClique no botão abaixo para participar!",
            color=discord.Color.gold()
        )
        view = SorteioView(valor_premio=valor)
        await interaction.response.send_message(embed=embed, view=view)

class SorteioView(ui.View):
    def __init__(self, valor_premio: int):
        super().__init__(timeout=None)
        self.valor_premio = valor_premio
        self.participantes = set()

    @ui.button(label="Participar 🎟️", style=discord.ButtonStyle.success)
    async def entrar(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id in self.participantes:
            await interaction.response.send_message("Você já está participando deste sorteio!", ephemeral=True)
        else:
            self.participantes.add(interaction.user.id)
            await interaction.response.send_message("Você entrou no sorteio com sucesso!", ephemeral=True)

    @ui.button(label="Encerrar Sorteio 🏆", style=discord.ButtonStyle.danger)
    async def encerrar(self, interaction: discord.Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Apenas administradores podem encerrar o sorteio.", ephemeral=True)
            return

        if not self.participantes:
            await interaction.response.send_message("Ninguém participou do sorteio!", ephemeral=True)
            return

        ganhador_id = random.choice(list(self.participantes))
        ganhador = interaction.guild.get_member(ganhador_id)

        # Adiciona os Chesscoins direto no Supabase
        adicionar_chesscoins(ganhador_id, self.valor_premio)

        await interaction.response.send_message(
            f"🎉 **Sorteio Encerrado!**\nParabéns {ganhador.mention}! Você ganhou **{self.valor_premio} 🪙 Chesscoins**!"
        )
        self.stop()

@bot.tree.command(name="sorteio", description="Abre o painel para criar um sorteio de Chesscoins.")
async def cmd_sorteio(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)
        return
    await interaction.response.send_modal(SorteioModal())

# Coloque o TOKEN do UrnaBot nas variáveis de ambiente da FadeHost como DISCORD_TOKEN
bot.run(os.getenv("DISCORD_TOKEN"))
