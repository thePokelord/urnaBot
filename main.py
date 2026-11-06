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

# -----------------------------------------------------------------------------
# BANCO DE DADOS EM MEMÓRIA (ESTADO DA ELEIÇÃO)
# -----------------------------------------------------------------------------
dados_eleicao = {
    "ativa": False,
    "votacao_aberta": False,
    "titulo": "",
    "descricao": "",
    "cargo_id": None,
    "candidatos": {},  # {user_id: {"nome": str, "proposta": str, "votos": int}}
    "eleitores_votaram": set()  # IDs dos usuários que já votaram
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
# FORMULÁRIO (MODAL) PARA CANDIDATURA (/candidatar-se)
# -----------------------------------------------------------------------------

class CandidaturaModal(ui.Modal, title="Formulário de Candidatura"):
    nome_campanha = ui.TextInput(
        label="Seu Nome / Nome de Campanha",
        placeholder="Ex.: Lorenzo",
        required=True,
        max_length=50
    )
    proposta = ui.TextInput(
        label="Sua Proposta ou Motivo",
        style=discord.TextStyle.paragraph,
        placeholder="Explique por que os membros devem votar em você...",
        required=True,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        if not dados_eleicao["ativa"]:
            await interaction.response.send_message("❌ **Erro:** Não há nenhuma eleição aberta no momento!", ephemeral=True)
            return

        if dados_eleicao["votacao_aberta"]:
            await interaction.response.send_message("❌ **Erro:** As candidaturas já foram encerradas pois a votação está em andamento!", ephemeral=True)
            return

        # Registra ou atualiza o candidato
        dados_eleicao["candidatos"][user_id] = {
            "nome": self.nome_campanha.value,
            "proposta": self.proposta.value,
            "votos": 0
        }

        embed = discord.Embed(
            title="✅ Candidatura Registrada com Sucesso!",
            description=f"**Candidato:** {interaction.user.mention} (`{self.nome_campanha.value}`)\n**Proposta:** {self.proposta.value}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# -----------------------------------------------------------------------------
# COMPONENTES DE VOTAÇÃO (/votar)
# -----------------------------------------------------------------------------

class VotacaoSelect(ui.Select):
    def __init__(self):
        options = []
        for cid, info in dados_eleicao["candidatos"].items():
            options.append(discord.SelectOption(
                label=info['nome'],
                value=str(cid),
                description=f"Proposta: {info['proposta'][:50]}..."
            ))

        super().__init__(
            placeholder="Selecione seu candidato na lista...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        if user_id in dados_eleicao["eleitores_votaram"]:
            await interaction.response.send_message("❌ **Acesso Negado:** Você já registrou o seu voto nesta eleição!", ephemeral=True)
            return

        candidato_id = int(self.values[0])
        dados_eleicao["candidatos"][candidato_id]["votos"] += 1
        dados_eleicao["eleitores_votaram"].add(user_id)

        nome_candidato = dados_eleicao["candidatos"][candidato_id]["nome"]
        await interaction.response.send_message(
            f"🗳️ **Voto Confirmado!** Você votou com sucesso em **{nome_candidato}**. Seu voto é secreto!",
            ephemeral=True
        )

class VotacaoView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(VotacaoSelect())

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
        placeholder="Descreva as regras ou observações...",
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
        dados_eleicao["ativa"] = True
        dados_eleicao["votacao_aberta"] = False
        dados_eleicao["titulo"] = self.titulo_eleicao.value
        dados_eleicao["descricao"] = self.descricao_eleicao.value
        
        # Trata o ID do cargo
        cargo_str = self.cargo_id.value.strip() if self.cargo_id.value else ""
        dados_eleicao["cargo_id"] = int(cargo_str) if cargo_str.isdigit() else None
        
        dados_eleicao["candidatos"].clear()
        dados_eleicao["eleitores_votaram"].clear()

        embed = discord.Embed(
            title=f"🗳️ **NOVA ELEIÇÃO CONFIGURADA:** {dados_eleicao['titulo']}",
            description=(
                f"{dados_eleicao['descricao']}\n\n"
                f"📌 **Status:** Inscrições abertas para candidatos!\n"
                f"👉 Use o comando `/candidatar-se` para registrar sua candidatura."
            ),
            color=discord.Color.blue()
        )
        if dados_eleicao["cargo_id"]:
            embed.add_field(name="🏆 Cargo em Disputa", value=f"<@&{dados_eleicao['cargo_id']}>", inline=False)

        await interaction.response.send_message("✅ **Eleição configurada com sucesso!**", ephemeral=True)
        await interaction.channel.send(content="@everyone Nova eleição configurada!", embed=embed)

# -----------------------------------------------------------------------------
# PAINEL DE CONTROLE DE ELEIÇÃO (DASHBOARD EFÊMERO)
# -----------------------------------------------------------------------------

class DashboardEleicaoView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="📝 Nova Eleição", style=discord.ButtonStyle.primary, custom_id="btn_abrir_form")
    async def abrir_formulario(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(CriarEleicaoModal())

    @ui.button(label="🚀 Iniciar Votação", style=discord.ButtonStyle.success, custom_id="btn_iniciar_votacao")
    async def iniciar_votacao(self, interaction: discord.Interaction, button: ui.Button):
        if not dados_eleicao["ativa"]:
            await interaction.response.send_message("❌ Crie uma eleição primeiro!", ephemeral=True)
            return

        if not dados_eleicao["candidatos"]:
            await interaction.response.send_message("❌ Não é possível iniciar sem nenhum candidato inscrito!", ephemeral=True)
            return

        dados_eleicao["votacao_aberta"] = True
        
        embed = discord.Embed(
            title=f"🗳️ **VOTAÇÃO ABERTA:** {dados_eleicao['titulo']}",
            description=(
                f"{dados_eleicao['descricao']}\n\n"
                f"🚨 **A urna eletrônica está oficialmente aberta!**\n\n"
                f"👉 Digite **/votar** no chat para escolher seu candidato e registrar seu voto com segurança."
            ),
            color=discord.Color.green()
        )
        
        # Lista os candidatos inscritos no anúncio público
        lista_candidatos = "\n".join([f"• **{info['nome']}** (<@{cid}>)" for cid, info in dados_eleicao["candidatos"].items()])
        embed.add_field(name="📋 Candidatos Concorrentes", value=lista_candidatos, inline=False)

        await interaction.response.send_message("🚀 **Votação iniciada publicamente!**", ephemeral=True)
        await interaction.channel.send(content="@everyone 🚨 **ATENÇÃO! A VOTAÇÃO FOI INICIADA!** Digitem `/votar` para participar!", embed=embed)

    @ui.button(label="🛑 Encerrar Votação", style=discord.ButtonStyle.danger, custom_id="btn_encerrar_votacao")
    async def encerrar_votacao(self, interaction: discord.Interaction, button: ui.Button):
        if not dados_eleicao["ativa"] or not dados_eleicao["votacao_aberta"]:
            await interaction.response.send_message("❌ Nenhuma votação está em andamento para ser encerrada!", ephemeral=True)
            return

        dados_eleicao["votacao_aberta"] = False
        dados_eleicao["ativa"] = False

        # Apuração dos votos
        candidatos = dados_eleicao["candidatos"]
        vencedor_id = max(candidatos, key=lambda cid: candidatos[cid]["votos"])
        vencedor_info = candidatos[vencedor_id]

        embed = discord.Embed(
            title=f"🏆 **RESULTADO FINAL DA ELEIÇÃO:** {dados_eleicao['titulo']}",
            description=f"A urna eletrônica foi encerrada! Confira a contagem dos votos:",
            color=discord.Color.gold()
        )

        for cid, info in candidatos.items():
            embed.add_field(
                name=f"Candidato: {info['nome']}",
                value=f"🗳️ **{info['votos']} voto(s)**",
                inline=True
            )

        embed.add_field(
            name="🎉 GRANDIOSO VENCEDOR",
            value=f"🥇 <@{vencedor_id}> (`{vencedor_info['nome']}`) com **{vencedor_info['votos']} votos**!",
            inline=False
        )

        # Entrega automática do cargo ao vencedor (se configurado)
        mensagem_cargo = ""
        if dados_eleicao["cargo_id"]:
            cargo = interaction.guild.get_role(dados_eleicao["cargo_id"])
            membro = interaction.guild.get_member(vencedor_id)
            if cargo and membro:
                try:
                    await membro.add_role(cargo)
                    mensagem_cargo = f"\n🎖️ O cargo {cargo.mention} foi atribuído automaticamente a <@{vencedor_id}>!"
                except Exception as e:
                    mensagem_cargo = f"\n⚠️ Não foi possível atribuir o cargo automaticamente (verifique as permissões do bot)."

        if mensagem_cargo:
            embed.add_field(name="Cargo Entregue", value=mensagem_cargo, inline=False)

        await interaction.response.send_message("🛑 **Votação encerrada com sucesso!**", ephemeral=True)
        await interaction.channel.send(content=f"@everyone 🛑 **VOTAÇÃO ENCERRADA!** Confira o resultado final abaixo:", embed=embed)

# -----------------------------------------------------------------------------
# COMANDOS DE BARRA (SLASH COMMANDS)
# -----------------------------------------------------------------------------

@bot.tree.command(name="criar_eleicao", description="Abre o painel de gerenciamento de eleições (Apenas ADM/Dono).")
async def criar_eleicao(interaction: discord.Interaction):
    e_dono = interaction.user.id == interaction.guild.owner_id
    e_adm = interaction.user.guild_permissions.administrator

    if not (e_dono or e_adm):
        await interaction.response.send_message("❌ **Acesso Negado!** Apenas Administradores ou o Criador podem usar este comando.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🗳️ **UrnaBot — Painel de Controle Eleitoral**",
        description="Painel Administrativo do **Dischesslord Hub**.\nUse os botões abaixo para gerenciar a eleição.",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, view=DashboardEleicaoView(), ephemeral=True)

@bot.tree.command(name="candidatar-se", description="Inscreva-se como candidato na eleição ativa.")
async def candidatar_se(interaction: discord.Interaction):
    if not dados_eleicao["ativa"]:
        await interaction.response.send_message("❌ Não há nenhuma eleição com inscrições abertas no momento!", ephemeral=True)
        return

    if dados_eleicao["votacao_aberta"]:
        await interaction.response.send_message("❌ As candidaturas já foram encerradas!", ephemeral=True)
        return

    await interaction.response.send_modal(CandidaturaModal())

@bot.tree.command(name="votar", description="Abra a urna secreta para votar em um candidato.")
async def votar(interaction: discord.Interaction):
    if not dados_eleicao["ativa"] or not dados_eleicao["votacao_aberta"]:
        await interaction.response.send_message("❌ Não há nenhuma votação aberta no momento!", ephemeral=True)
        return

    if interaction.user.id in dados_eleicao["eleitores_votaram"]:
        await interaction.response.send_message("❌ Você já registrou seu voto nesta eleição!", ephemeral=True)
        return

    if not dados_eleicao["candidatos"]:
        await interaction.response.send_message("❌ Nenhum candidato encontrado para esta votação.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🗳️ **Urna Eletrônica — Cabine Secreta**",
        description="Escolha seu candidato no menu suspenso abaixo para confirmar seu voto:",
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed, view=VotacaoView(), ephemeral=True)

# -----------------------------------------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------------------------------------

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("ERRO CRÍTICO: O token não foi configurado nas Variáveis de Ambiente!")

bot.run(TOKEN)
