import os
import discord
from discord.ext import commands
from discord import app_commands, ui

# Configuração de intenções
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class UrnaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
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
# FORMULÁRIO (MODAL) PARA CRIAR ELEIÇÃO
# -----------------------------------------------------------------------------

class CriarEleicaoModal(ui.Modal, title="Criar Nova Eleição"):
    titulo_eleicao = ui.TextInput(
        label="Título da Eleição",
        placeholder="Ex.: Eleição para Moderador 2026",
        required=True,
        max_length=100
    )

    descricao_eleicao = ui.TextInput(
        label="Descrição da Eleição",
        style=discord.TextStyle.paragraph,
        placeholder="Descreva as regras, os cargos disponíveis ou observações...",
        required=True,
        max_length=1000
    )

    cargo_id = ui.TextInput(
        label="ID do Cargo a ser Concedido (Opcional)",
        placeholder="Ex.: 123456789012345678",
        required=False,
        max_length=20
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Aqui o formulário é processado quando o ADM clica em "Enviar"
        titulo = self.titulo_eleicao.value
        descricao = self.descricao_eleicao.value
        cargo = self.cargo_id.value or "Nenhum cargo atrelado"

        embed = discord.Embed(
            title=f"🗳️ Nova Eleição: {titulo}",
            description=f"{descricao}\n\n**Cargo em disputa:** {cargo}",
            color=discord.Color.green()
        )
        embed.set_footer(text="Votação gerenciada pelo UrnaBot")

        await interaction.response.send_message(
            content="✅ **Eleição criada e enviada com sucesso!**",
            embed=embed,
            ephemeral=False  # Essa mensagem pública é a urna enviada no canal
        )

# -----------------------------------------------------------------------------
# PAINEL DE CONTROLE DE ELEIÇÃO (DASHBOARD EFÊMERO)
# -----------------------------------------------------------------------------

class DashboardEleicaoView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="📝 Nova Eleição (Formulário)", style=discord.ButtonStyle.primary, custom_id="btn_abrir_form")
    async def abrir_formulario(self, interaction: discord.Interaction, button: ui.Button):
        # Abre a janela pop-up do formulário
        await interaction.response.send_modal(CriarEleicaoModal())

    @ui.button(label="🗳️ Iniciar Votação", style=discord.ButtonStyle.success, custom_id="btn_iniciar_votacao")
    async def iniciar_votacao(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("🚀 **Votação Iniciada!** A urna eletrônica está aberta.", ephemeral=True)

    @ui.button(label="🔒 Encerrar Votação", style=discord.ButtonStyle.secondary, custom_id="btn_encerrar_votacao")
    async def encerrar_votacao(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("🛑 **Votação Encerrada!** A urna foi trancada.", ephemeral=True)

# -----------------------------------------------------------------------------
# COMANDO DE BARRA /criar_eleicao
# -----------------------------------------------------------------------------

@bot.tree.command(name="criar_eleicao", description="Abre o painel de gerenciamento de eleições (Apenas ADM/Dono).")
async def criar_eleicao(interaction: discord.Interaction):
    # Verificação de permissões
    e_dono = interaction.user.id == interaction.guild.owner_id
    e_adm = interaction.user.guild_permissions.administrator

    if not (e_dono or e_adm):
        await interaction.response.send_message(
            "❌ **Acesso Negado!** Apenas Administradores ou o Criador do servidor podem acessar o Painel.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🗳️ **UrnaBot — Painel de Controle Eleitoral**",
        description=(
            "Painel de Gerenciamento do **Dischesslord Hub**.\n\n"
            "Clique em **Nova Eleição** para abrir o formulário e configurar o título, a descrição e o cargo."
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text="Painel Administrativo Privado")

    # ephemeral=True faz com que APENAS o ADM veja a mensagem no chat
    await interaction.response.send_message(embed=embed, view=DashboardEleicaoView(), ephemeral=True)

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("ERRO CRÍTICO: O token não foi configurado nas Variáveis de Ambiente!")

bot.run(TOKEN)
