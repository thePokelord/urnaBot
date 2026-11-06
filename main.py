import os
import random
import discord
from discord.ext import commands
from discord import app_commands, ui
from supabase import create_client, Client

# Configuração de intenções
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class UrnaBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        synced = await self.tree.sync()
        print(f"✅ Sincronizados {len(synced)} comandos de barra globalmente!")

bot = UrnaBot()

# -----------------------------------------------------------------------------
# SISTEMA DE BANCO DE DADOS COMPARTILHADO (SUPABASE - CHESSCOINS)
# -----------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None

def obter_chesscoins(user_id: int) -> int:
    if not supabase:
        return 0
    try:
        res = supabase.table("chesscoins").select("saldo").eq("user_id", str(user_id)).execute()
        if res.data:
            return res.data[0]["saldo"]
        return 0
    except Exception as e:
        print(f"Erro ao ler saldo no Supabase: {e}")
        return 0

def adicionar_chesscoins(user_id: int, quantia: int):
    if not supabase or quantia <= 0:
        return
    saldo_atual = obter_chesscoins(user_id)
    novo_saldo = saldo_atual + quantia
    try:
        supabase.table("chesscoins").upsert(
            {"user_id": str(user_id), "saldo": novo_saldo}
        ).execute()
    except Exception as e:
        print(f"Erro ao salvar saldo no Supabase: {e}")

# -----------------------------------------------------------------------------
# BANCO DE DADOS EM MEMÓRIA (ELEIÇÃO E SORTEIO)
# -----------------------------------------------------------------------------
dados_eleicao = {
    "ativa": False,
    "votacao_aberta": False,
    "titulo": "",
    "descricao": "",
    "cargo_id": None,
    "candidatos": {},
    "eleitores_votaram": set()
}

dados_sorteio = {
    "ativo": False,
    "titulo": "",
    "descricao": "",
    "cargo_id": None,
    "chesscoins": 0,
    "qtd_ganhadores": 1,
    "participantes": set()
}

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
# PAINEL E FORMULÁRIO DE SORTEIO
# -----------------------------------------------------------------------------

class SorteioParticiparView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="🎉 Entrar no Sorteio", style=discord.ButtonStyle.success, custom_id="btn_entrar_sorteio")
    async def entrar_sorteio(self, interaction: discord.Interaction, button: ui.Button):
        if not dados_sorteio["ativo"]:
            await interaction.response.send_message("❌ Não há nenhum sorteio ativo no momento!", ephemeral=True)
            return

        user_id = interaction.user.id
        if user_id in dados_sorteio["participantes"]:
            await interaction.response.send_message("⚠️ Você já está participando deste sorteio!", ephemeral=True)
            return

        dados_sorteio["participantes"].add(user_id)
        qtd = len(dados_sorteio["participantes"])
        await interaction.response.send_message(f"✅ **Presença confirmada!** Você entrou no sorteio. Total de participantes: `{qtd}`", ephemeral=True)

class CriarSorteioModal(ui.Modal, title="Criar Novo Sorteio"):
    titulo_sorteio = ui.TextInput(
        label="Título do Sorteio",
        placeholder="Ex.: Sorteio Cargo Modo Lento? Nah",
        required=True,
        max_length=100
    )
    descricao_sorteio = ui.TextInput(
        label="Descrição do Sorteio",
        style=discord.TextStyle.paragraph,
        placeholder="Explique o prêmio, regras e quando será o sorteio...",
        required=True,
        max_length=500
    )
    cargo_id = ui.TextInput(
        label="ID do Cargo de Prêmio (Opcional)",
        placeholder="Ex.: 123456789012345678",
        required=False,
        max_length=20
    )
    chesscoins = ui.TextInput(
        label="Prêmio em Chesscoins (Opcional)",
        placeholder="Ex.: 500",
        required=False,
        max_length=10
    )
    ganhadores = ui.TextInput(
        label="Quantidade de Vencedores",
        placeholder="Padrão: 1",
        default="1",
        required=False,
        max_length=2
    )

    async def on_submit(self, interaction: discord.Interaction):
        dados_sorteio["ativo"] = True
        dados_sorteio["titulo"] = self.titulo_sorteio.value
        dados_sorteio["descricao"] = self.descricao_sorteio.value
        
        c_str = self.cargo_id.value.strip() if self.cargo_id.value else ""
        dados_sorteio["cargo_id"] = int(c_str) if c_str.isdigit() else None

        coins_str = self.chesscoins.value.strip() if self.chesscoins.value else "0"
        dados_sorteio["chesscoins"] = int(coins_str) if coins_str.isdigit() else 0

        g_str = self.ganhadores.value.strip() if self.ganhadores.value else "1"
        dados_sorteio["qtd_ganhadores"] = int(g_str) if g_str.isdigit() and int(g_str) > 0 else 1

        dados_sorteio["participantes"].clear()

        embed = discord.Embed(
            title=f"🎉 **NOVO SORTEIO:** {dados_sorteio['titulo']}",
            description=f"{dados_sorteio['descricao']}\n\n👉 **Clique no botão abaixo para participar!**",
            color=discord.Color.gold()
        )

        premios = []
        if dados_sorteio["cargo_id"]:
            premios.append(f"🎖️ Cargo: <@&{dados_sorteio['cargo_id']}>")
        if dados_sorteio["chesscoins"] > 0:
            premios.append(f"🪙 **{dados_sorteio['chesscoins']} Chesscoins**")

        if premios:
            embed.add_field(name="🎁 Prêmios", value="\n".join(premios), inline=False)
        embed.add_field(name="👥 Vencedores", value=f"`{dados_sorteio['qtd_ganhadores']}` sortead(os)", inline=True)

        await interaction.response.send_message("✅ **Sorteio publicado com sucesso!**", ephemeral=True)
        await interaction.channel.send(content="@everyone 🎉 **NOVO SORTEIO NO DISCHESSLORD HUB!**", embed=embed, view=SorteioParticiparView())

class DashboardSorteioView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="🎁 Criar Sorteio", style=discord.ButtonStyle.primary, custom_id="btn_abrir_sorteio_form")
    async def abrir_form(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(CriarSorteioModal())

    @ui.button(label="🎲 Realizar Sorteio", style=discord.ButtonStyle.success, custom_id="btn_realizar_sorteio")
    async def realizar_sorteio(self, interaction: discord.Interaction, button: ui.Button):
        if not dados_sorteio["ativo"]:
            await interaction.response.send_message("❌ Não há nenhum sorteio configurado!", ephemeral=True)
            return

        participantes = list(dados_sorteio["participantes"])
        if not participantes:
            await interaction.response.send_message("❌ Ninguém entrou no sorteio ainda!", ephemeral=True)
            return

        dados_sorteio["ativo"] = False
        qtd = min(len(participantes), dados_sorteio["qtd_ganhadores"])
        vencedores_ids = random.sample(participantes, qtd)

        mencoes = []
        for vid in vencedores_ids:
            mencoes.append(f"<@{vid}>")
            # Concede o cargo (se configurado)
            if dados_sorteio["cargo_id"]:
                cargo = interaction.guild.get_role(dados_sorteio["cargo_id"])
                membro = interaction.guild.get_member(vid)
                if cargo and membro:
                    try:
                        await membro.add_role(cargo)
                    except Exception:
                        pass
            # Concede Chesscoins direto no Supabase (se configurado)
            if dados_sorteio["chesscoins"] > 0:
                adicionar_chesscoins(vid, dados_sorteio["chesscoins"])

        embed = discord.Embed(
            title=f"🎊 **RESULTADO DO SORTEIO:** {dados_sorteio['titulo']}",
            description=f"Parabéns aos vencedores da rodada!\n\n🏆 **Ganhadores:**\n" + "\n".join(mencoes),
            color=discord.Color.green()
        )

        if dados_sorteio["chesscoins"] > 0:
            embed.add_field(name="🪙 Chesscoins", value=f"Cada vencedor recebeu `+{dados_sorteio['chesscoins']}` Chesscoins no banco da nuvem!", inline=False)

        await interaction.response.send_message("🎲 **Sorteio realizado!**", ephemeral=True)
        await interaction.channel.send(content=f"@everyone 🎊 **TEMOS GANHADORES NO SORTEIO!**", embed=embed)

# -----------------------------------------------------------------------------
# PAINEL ELEITORAL (MODAL E DASHBOARD)
# -----------------------------------------------------------------------------

class CandidaturaModal(ui.Modal, title="Formulário de Candidatura"):
    nome_campanha = ui.TextInput(label="Seu Nome / Nome de Campanha", placeholder="Ex.: Lorenzo", required=True, max_length=50)
    proposta = ui.TextInput(label="Sua Proposta ou Motivo", style=discord.TextStyle.paragraph, placeholder="Explique por que devem votar em você...", required=True, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if not dados_eleicao["ativa"] or dados_eleicao["votacao_aberta"]:
            await interaction.response.send_message("❌ Inscrições indisponíveis no momento!", ephemeral=True)
            return

        dados_eleicao["candidatos"][user_id] = {"nome": self.nome_campanha.value, "proposta": self.proposta.value, "votos": 0}
        embed = discord.Embed(title="✅ Candidatura Registrada!", description=f"**Candidato:** {interaction.user.mention} (`{self.nome_campanha.value}`)\n**Proposta:** {self.proposta.value}", color=discord.Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True)

class VotacaoSelect(ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=info['nome'], value=str(cid), description=f"Proposta: {info['proposta'][:50]}...") for cid, info in dados_eleicao["candidatos"].items()]
        super().__init__(placeholder="Selecione seu candidato na lista...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        if user_id in dados_eleicao["eleitores_votaram"]:
            await interaction.response.send_message("❌ Você já votou nesta eleição!", ephemeral=True)
            return

        candidato_id = int(self.values[0])
        dados_eleicao["candidatos"][candidato_id]["votos"] += 1
        dados_eleicao["eleitores_votaram"].add(user_id)
        await interaction.response.send_message(f"🗳️ **Voto registrado em {dados_eleicao['candidatos'][candidato_id]['nome']}!** (Secreto)", ephemeral=True)

class VotacaoView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VotacaoSelect())

class CriarEleicaoModal(ui.Modal, title="Criar Nova Eleição"):
    titulo_eleicao = ui.TextInput(label="Título da Eleição", placeholder="Ex.: Eleição para Moderador 2026", required=True, max_length=100)
    descricao_eleicao = ui.TextInput(label="Descrição da Eleição", style=discord.TextStyle.paragraph, placeholder="Descreva as regras...", required=True, max_length=1000)
    cargo_id = ui.TextInput(label="ID do Cargo a Conceder (Opcional)", placeholder="Ex.: 123456789012345678", required=False, max_length=20)

    async def on_submit(self, interaction: discord.Interaction):
        dados_eleicao["ativa"] = True
        dados_eleicao["votacao_aberta"] = False
        dados_eleicao["titulo"] = self.titulo_eleicao.value
        dados_eleicao["descricao"] = self.descricao_eleicao.value
        c_str = self.cargo_id.value.strip() if self.cargo_id.value else ""
        dados_eleicao["cargo_id"] = int(c_str) if c_str.isdigit() else None
        dados_eleicao["candidatos"].clear()
        dados_eleicao["eleitores_votaram"].clear()

        embed = discord.Embed(
            title=f"🗳️ **NOVA ELEIÇÃO:** {dados_eleicao['titulo']}",
            description=f"{dados_eleicao['descricao']}\n\n👉 Use **/candidatar_se** para se inscrever!",
            color=discord.Color.blue()
        )
        await interaction.response.send_message("✅ **Eleição criada com sucesso!**", ephemeral=True)
        await interaction.channel.send(content="@everyone Nova eleição configurada!", embed=embed)

class DashboardEleicaoView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="📝 Nova Eleição", style=discord.ButtonStyle.primary, custom_id="btn_abrir_form")
    async def abrir_form(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(CriarEleicaoModal())

    @ui.button(label="🚀 Iniciar Votação", style=discord.ButtonStyle.success, custom_id="btn_iniciar_votacao")
    async def iniciar_votacao(self, interaction: discord.Interaction, button: ui.Button):
        if not dados_eleicao["ativa"] or not dados_eleicao["candidatos"]:
            await interaction.response.send_message("❌ Crie a eleição e aguarde candidatos inscritos!", ephemeral=True)
            return

        dados_eleicao["votacao_aberta"] = True
        embed = discord.Embed(title=f"🗳️ **VOTAÇÃO ABERTA:** {dados_eleicao['titulo']}", description=f"👉 Digite **/votar** para votar!", color=discord.Color.green())
        await interaction.response.send_message("🚀 **Votação iniciada!**", ephemeral=True)
        await interaction.channel.send(content="@everyone 🚨 **VOTAÇÃO ABERTA!** Use `/votar`!", embed=embed)

    @ui.button(label="🛑 Encerrar Votação", style=discord.ButtonStyle.danger, custom_id="btn_encerrar_votacao")
    async def encerrar_votacao(self, interaction: discord.Interaction, button: ui.Button):
        if not dados_eleicao["ativa"] or not dados_eleicao["votacao_aberta"]:
            await interaction.response.send_message("❌ Nenhuma votação ativa para encerrar!", ephemeral=True)
            return

        dados_eleicao["votacao_aberta"] = False
        dados_eleicao["ativa"] = False
        candidatos = dados_eleicao["candidatos"]
        vencedor_id = max(candidatos, key=lambda cid: candidatos[cid]["votos"])

        embed = discord.Embed(title=f"🏆 **RESULTADO FINAL:** {dados_eleicao['titulo']}", color=discord.Color.gold())
        embed.add_field(name="🎉 VENCEDOR", value=f"🥇 <@{vencedor_id}> com {candidatos[vencedor_id]['votos']} votos!", inline=False)

        if dados_eleicao["cargo_id"]:
            cargo = interaction.guild.get_role(dados_eleicao["cargo_id"])
            membro = interaction.guild.get_member(vencedor_id)
            if cargo and membro:
                try:
                    await membro.add_role(cargo)
                except Exception:
                    pass

        await interaction.response.send_message("🛑 **Encerrado!**", ephemeral=True)
        await interaction.channel.send(content="@everyone 🛑 **VOTAÇÃO ENCERRADA!**", embed=embed)

# -----------------------------------------------------------------------------
# COMANDOS DE BARRA (SLASH COMMANDS)
# -----------------------------------------------------------------------------

def checar_adm(interaction: discord.Interaction):
    return interaction.user.id == interaction.guild.owner_id or interaction.user.guild_permissions.administrator

@bot.tree.command(name="criar_eleicao", description="Painel de gerenciamento de eleições (Apenas ADM).")
async def criar_eleicao(interaction: discord.Interaction):
    if not checar_adm(interaction):
        await interaction.response.send_message("❌ Acesso Negado!", ephemeral=True)
        return
    embed = discord.Embed(title="🗳️ **UrnaBot — Painel Eleitoral**", color=discord.Color.blue())
    await interaction.response.send_message(embed=embed, view=DashboardEleicaoView(), ephemeral=True)

@bot.tree.command(name="sorteio", description="Painel de gerenciamento de sorteios (Apenas ADM).")
async def sorteio(interaction: discord.Interaction):
    if not checar_adm(interaction):
        await interaction.response.send_message("❌ Acesso Negado!", ephemeral=True)
        return
    embed = discord.Embed(
        title="🎁 **UrnaBot — Painel de Sorteios**",
        description="Clique em **Criar Sorteio** para abrir o formulário e configurar o prêmio (Cargo e/ou Chesscoins).",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed, view=DashboardSorteioView(), ephemeral=True)

@bot.tree.command(name="candidatar_se", description="Inscreva-se como candidato na eleição ativa.")
async def candidatar_se(interaction: discord.Interaction):
    await interaction.response.send_modal(CandidaturaModal())

@bot.tree.command(name="votar", description="Abra a urna secreta para votar.")
async def votar(interaction: discord.Interaction):
    if not dados_eleicao["ativa"] or not dados_eleicao["votacao_aberta"]:
        await interaction.response.send_message("❌ Nenhuma votação aberta!", ephemeral=True)
        return
    embed = discord.Embed(title="🗳️ **Urna Secreta**", description="Escolha seu candidato:", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed, view=VotacaoView(), ephemeral=True)

@bot.tree.command(name="saldo", description="Veja seu saldo de Chesscoins.")
async def saldo(interaction: discord.Interaction):
    qtd = obter_chesscoins(interaction.user.id)
    await interaction.response.send_message(f"🪙 **{interaction.user.display_name}**, você possui **{qtd} Chesscoins** no banco global!", ephemeral=True)

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("ERRO CRÍTICO: O token não foi configurado nas Variáveis de Ambiente!")

bot.run(TOKEN)
