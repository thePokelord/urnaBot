TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "A variável de ambiente DISCORD_TOKEN não foi configurada."
    ) 