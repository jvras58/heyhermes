# HeyHermes 🪽

Assistente de voz local estilo Jarvis: fica escutando a wake word, transcreve seu
comando, pensa com o [hermes-agent da NousResearch](https://github.com/NousResearch/hermes-agent)
(rodando em Docker, com terminal, arquivos, web, memória e skills próprios) e
responde falando com o Piper.

```
wake word (openWakeWord) → gravação → STT (Faster-Whisper) → hermes-agent (Docker) → TTS (Piper)
```

Inspirado na onda de assistentes estilo Jarvis, como o
[jarvis_ai](https://github.com/eadmin2/jarvis_ai).

## Estrutura

```
heyhermes/
├── .env                       # sua configuração (copie de .env.example)
├── docker-compose.yml         # hermes-agent com API OpenAI-compatível
├── hermes-data/               # config, sessões e memórias do hermes (gitignored)
├── pyproject.toml
└── src/heyhermes/
    ├── core/config.py         # central de configurações (Pydantic-Settings)
    ├── audio/
    │   ├── wake_word.py       # loop de escuta da wake word (openWakeWord)
    │   ├── stt.py             # gravação + transcrição (Faster-Whisper)
    │   └── tts.py             # voz em streaming (Piper, 100% local)
    ├── agent/brain.py         # conversa com o hermes-agent via API
    └── main.py                # loop principal
```

## Setup

Requisitos: microfone, [uv](https://docs.astral.sh/uv/), Docker e — para o modelo
local padrão — [Ollama](https://ollama.com) com `qwen2.5:7b`.

```powershell
# 1. dependências
uv sync

# 2. voz do Piper (pt-BR)
uv run python -m piper.download_voices pt_BR-faber-medium --data-dir models/piper

# 3. configuração (gere uma HERMES_API_KEY longa)
copy .env.example .env

# 4. sobe o hermes-agent
docker compose up -d

# 5. rodar
uv run heyhermes
```

Diga **"Hey Jarvis"** (wake word padrão), espere o "Sim?" e fale o comando.

**Modo conversa:** depois de cada resposta o assistente continua escutando —
não precisa repetir a wake word. Se você ficar em silêncio por
`SPEECH_START_TIMEOUT` segundos (padrão 6), ele volta a dormir. Para exigir a
wake word a cada comando, ponha `FOLLOW_UP=false` no `.env`.

Comandos pré-definidos (sem passar pelo LLM): **"desligar" / "encerrar"**
finaliza, **"cancelar"** volta a dormir.

> Setup completo do hermes (modelo, provedores, dashboard, troubleshooting):
> **[docs/hermes-setup.md](docs/hermes-setup.md)**

## Relatórios do banco + abrir o navegador 📊

O agente pode consultar um **PostgreSQL seu**, montar um relatório HTML (tabela
+ gráfico) e **abrir na sua tela**, além de abrir sites no seu navegador — tudo
por voz:

- *"Me mostra o total de vendas por categoria."* → ele descobre as tabelas,
  escreve o SQL, gera o relatório, abre no navegador e fala um resumo.
- *"Abre o site da Nous Research."* → abre no seu navegador padrão.

O acesso ao banco é **isolado e somente-leitura**: quem fala com o banco é um
servidor MCP dedicado (**DBHub**, no container `db-mcp`) que guarda a conexão —
o agente nunca vê a senha e só ganha tools read-only (`search_objects`,
`execute_sql`). O relatório é montado por um renderizador sem acesso a banco, e
a ponte de mostrar na tela usa mounts (`./reports`) + diretivas no texto.

**Testar na hora, sem ter um banco** — sobe um Postgres de exemplo (mini-loja):

```env
HEYHERMES_PG_DSN=postgres://hermes:hermes@demo-db:5432/loja?sslmode=disable
```

```powershell
docker compose --profile demo up -d
docker compose exec hermes hermes mcp add banco --url http://db-mcp:8080/mcp
```

**Com o seu banco** — aponte o `.env` (esquema `postgres://`) e use `--profile db`.
O DBHub é multi-banco, então trocar para MySQL/MariaDB, SQLite ou SQL Server é só
mudar o DSN. Guia completo (arquitetura MCP, banco demo, trocar de banco,
segurança, troubleshooting):
**[docs/relatorios-e-navegador.md](docs/relatorios-e-navegador.md)**

> **Adicionando mais ferramentas?** Prefira **plugar um MCP no hermes** a
> escrever tools diretas — isola credenciais e qualquer um estende com 1–2
> comandos. Princípio e passo a passo em
> **[docs/estendendo-com-mcp.md](docs/estendendo-com-mcp.md)**.

## Trocando o modelo do hermes

O modelo/provedor fica no próprio hermes — o heyhermes não precisa mudar nada.

**Modelo local (Ollama):** edite `hermes-data/config.yaml` e reinicie:

```yaml
model:
  default: qwen2.5:7b                              # troque pelo modelo desejado
  provider: custom
  base_url: http://host.docker.internal:11434/v1   # Ollama do host
  context_length: 65536                            # hermes exige mínimo de 64K
  ollama_num_ctx: 65536
```

```powershell
ollama pull <novo-modelo>
docker compose restart hermes
```

**Provedor forte (recomendado):** modelos 7B se atrapalham com o prompt
agêntico do hermes — para o fluxo de relatórios eles simplesmente não dão
conta. O wizard configura Nous Portal, OpenRouter, OpenAI etc.:

```powershell
docker compose run --rm hermes model     # wizard interativo
docker compose restart hermes
```

Com o container **já rodando**, prefira `exec` (instantâneo — `run --rm` cria
um container novo e parece travado):

```powershell
docker compose exec hermes hermes config set OPENROUTER_API_KEY sua-chave
```

> Endpoints OpenAI-compatíveis (NVIDIA NIM, Groq…), o padrão `key_env` e os
> erros comuns de Docker estão em
> **[docs/hermes-setup.md](docs/hermes-setup.md#4-modelo--provedor-llm)**.

## Wake word "Hey Hermes"

O openWakeWord só tem modelos pré-treinados genéricos (`hey_jarvis`, `alexa`…).
Para responder a "Hey Hermes", treine um modelo customizado com o
[notebook oficial de treino do openWakeWord](https://github.com/dscripka/openWakeWord#training-new-models)
(roda no Colab em ~1h, gera um `.onnx`) e aponte no `.env`:

```env
WAKE_WORDS=["models/wake/hey_hermes.onnx"]
```

Alternativa: [Picovoice Porcupine](https://picovoice.ai/) treina "Hey Hermes" na
hora no console web (grátis para uso pessoal, exige access key).

## Dashboard do hermes

Interface web do agente (sessões, memórias, skills e chat) em
**http://localhost:9119/login**. O login usa o usuário e o hash de senha
definidos em `hermes-data/config.yaml` (`dashboard.basic_auth`) — o passo a
passo de como criar essas credenciais está no
[guia de setup](docs/hermes-setup.md#5-dashboard-web).

## Problemas comuns

**Wake word não dispara** — os modelos pré-treinados do openWakeWord são
treinados com pronúncia **inglesa**: fale "hey JAR-vis" / "ah-LEK-sah" puxado
pro inglês. Pronúncia brasileira pontua ~0.05 (limiar: 0.5). A solução
definitiva é treinar um modelo pt-BR (seção acima).

**Nada responde e o log mostra "Nível ambiente do microfone: RMS" muito baixo
(< 10)** — o mic padrão do Windows não é o que você está usando (headset
desconectado faz o padrão cair pro mic interno). Conecte o headset ou escolha
o dispositivo no `.env`:

```env
INPUT_DEVICE=1       # índice de: uv run python -m sounddevice
INPUT_GAIN=1.0       # ganho de software p/ mics fracos (suba SILENCE_THRESHOLD junto)
```

O heyhermes captura na taxa nativa do dispositivo e reamostra para 16 kHz por
software ([audio/mic.py](src/heyhermes/audio/mic.py)) — drivers como o Intel
Smart Sound ignoram a taxa pedida e entregariam áudio "esticado".

## Segurança

As tools do hermes (terminal, arquivos, web) rodam **dentro do container**, não
no seu Windows — o que também serve de sandbox. A API (`localhost:8642`) e o
dashboard (`localhost:9119`) só escutam em localhost e exigem autenticação.
