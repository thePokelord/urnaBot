import os
import discord
from discord.ext import commands
from discord import app_commands

# Configuração de intenções
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class UrnaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Sincroniza os comandos de barra com o Discord ao iniciar
        await self.tree.sync()
        print("Comandos de barra (slash commands) sincronizados com sucesso!")

bot = UrnaBot()

@bot.event
async def on_ready():
    print(f"----------------------------------------")
    print(f"UrnaBot conectado com sucesso!")
    print(f"Logado como: {bot.user.name} (ID: {bot.user.id})")
    print(f"----------------------------------------")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name="as eleições do Dischesslord Hub"
        )
    )

# -----------------------------------------------------------------------------
# PAINEL DE CONTROLE DE ELEIÇÃO (DASHBOARD)
# -----------------------------------------------------------------------------

class DashboardEleicaoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Mantém os botões ativos sem expirar

    @discord.ui.button(label="📝 Abrir Candidaturas", style=discord.ButtonStyle.primary, custom_id="btn_abrir_candidaturas")
    async def abrir_candidaturas(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📌 **Inscrições Abertas!** Os membros agora podem se candidatar às vagas disponíveis.", ephemeral=False)

    @discord.ui.button(label="🗳️ Iniciar Votação", style=discord.ButtonStyle.success, custom_id="btn_iniciar_votacao")
    async def iniciar_votacao(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚀 **Votação Iniciada!** A urna eletrônica está aberta para os votos.", ephemeral=False)

    @discord.ui.button(label="🔒 Encerrar Votação", style=discord.ButtonStyle.secondary, custom_id="btn_encerrar_votacao")
    async def encerrar_votacao(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🛑 **Votação Encerrada!** A urna foi trancada. Contabilizando os votos...", ephemeral=False)

    @discord.ui.button(label="📊 Ver Resultados", style=discord.ButtonStyle.danger, custom_id="btn_ver_resultados")
    async def ver_resultados(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🏆 **Resultado da Eleição:** Os relatórios de votos e cargos distribuídos serão exibidos aqui.", ephemeral=False)

# -----------------------------------------------------------------------------
# COMANDO DE BARRA /criar_eleicao
# -----------------------------------------------------------------------------

@bot.tree.command(name="criar_eleicao", description="Abre o painel principal de gerenciamento de eleições (Apenas ADM/Dono).")
async def criar_eleicao(interaction: discord.Interaction):
    # Verificação: Usuário é o Dono do Servidor OU tem permissão de Administrador?
    e_dono = interaction.user.id == interaction.guild.owner_id
    e_adm = interaction.user.guild_permissions.administrator

    if not (e_dono or e_adm):
        await interaction.response.send_message(
            "❌ **Acesso Negado!** Apenas Administradores ou o Criador do servidor podem acessar o Painel Eleitoral.",
            ephemeral=True
        )
        return

    # Criação do Embed do Dashboard
    embed = discord.Embed(
        title="🗳️ **UrnaBot — Painel de Controle Eleitoral**",
        description=(
            "Bem-vindo ao painel central do **Dischesslord Hub**!\n\n"
            "Utilize os botões abaixo para gerenciar os ciclos das eleições no servidor. "
            "Apenas membros com privilégio administrativo conseguem acionar estes botões.\n\n"
            "• **Status da Urna:** 🟢 Online & Pronta\n"
            "• **Servidor:** Dischesslord Hub"
        ),
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=bot.user.display_avatar.url if bot.user.avatar else None)
    embed.set_footer(text="UrnaBot • Sistema Oficial de Eleições", icon_url=bot.user.display_avatar.url if bot.user.avatar else None)

    # Envia o painel com os botões
    await interaction.response.send_message(embed=embed, view=DashboardEleicaoView())

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("ERRO CRÍTICO: O token não foi configurado nas Variáveis de Ambiente da hospedagem!")

bot.run(TOKEN)
