# HeyHermes 🪽

Assistente de voz local estilo Jarvis: fica escutando a wake word, transcreve seu
comando, pensa com um LLM que tem "mãos" (tools) e responde falando com o Piper.

```
wake word (openWakeWord) → gravação → STT (Faster-Whisper) → agente (LLM + tools) → TTS (Piper)
```

Inspirado na onda de assistentes estilo Jarvis (como o
[jarvis_ai](https://github.com/eadmin2/jarvis_ai)), com integração opcional ao
[hermes-agent da NousResearch](https://github.com/NousResearch/hermes-agent).

## Estrutura

```
heyhermes/
├── .env                       # sua configuração (copie de .env.example)
├── pyproject.toml
└── src/heyhermes/
    ├── core/config.py         # central de configurações (Pydantic-Settings)
    ├── audio/
    │   ├── wake_word.py       # loop de escuta da wake word (openWakeWord)
    │   ├── stt.py             # gravação + transcrição (Faster-Whisper)
    │   └── tts.py             # voz (Piper, 100% local)
    ├── agent/
    │   ├── brain.py           # backends: ollama | openai | hermes-cli
    │   └── tools.py           # as "mãos": abrir apps, sites, hora, PowerShell
    └── main.py                # loop principal
```

## Setup

Requisitos: Windows/Linux/macOS com microfone, [uv](https://docs.astral.sh/uv/) e
(para o backend padrão) [Ollama](https://ollama.com) instalado.

```powershell
# 1. dependências
uv sync

# 2. voz do Piper (pt-BR)
uv run python -m piper.download_voices pt_BR-faber-medium --data-dir models/piper

# 3. modelo local com tool-calling
ollama pull qwen2.5:7b

# 4. configuração
copy .env.example .env

# 5. rodar
uv run heyhermes
```

Diga **"Hey Jarvis"** (wake word padrão), espere o "Sim?" e fale o comando:
*"que horas são?"*, *"abre o YouTube"*, *"abre o bloco de notas"*…

Comandos pré-definidos (sem passar pelo LLM): **"desligar" / "encerrar"** finaliza,
**"cancelar"** volta a dormir.

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

## Backends do cérebro

| Backend | Descrição |
|---|---|
| `ollama` | LLM local via Ollama com as tools deste projeto |
| `openai` | Qualquer endpoint OpenAI-compatível (OpenAI, OpenRouter, Nous Portal…) |
| `hermes` | [hermes-agent da NousResearch](https://github.com/NousResearch/hermes-agent) via Docker — agente completo com as próprias tools (terminal, arquivos, web, memória, skills) |

## hermes-agent via Docker

O [docker-compose.yml](docker-compose.yml) sobe o hermes-agent com a API
OpenAI-compatível habilitada na porta 8642 (só localhost). A chave em
`HERMES_API_KEY` no `.env` é compartilhada entre o container e o heyhermes.

```powershell
docker compose up -d      # sobe o gateway
uv run heyhermes          # heyhermes já aponta pra ele (BACKEND=hermes no .env)
```

Os dados do hermes (config, sessões, memórias) persistem em `./hermes-data/`.
O provedor LLM do hermes fica em `hermes-data/config.yaml` — por padrão
apontamos para o **Ollama do host** (100% local, sem chave externa):

```yaml
model:
  default: qwen2.5:7b
  provider: custom
  base_url: http://host.docker.internal:11434/v1
  context_length: 65536   # hermes exige mínimo de 64K de contexto
  ollama_num_ctx: 65536
```

Modelos 7B funcionam mas se atrapalham com o prompt agêntico do hermes.
Para respostas muito melhores, conecte um provedor forte (Nous Portal,
OpenRouter…) com o wizard: `docker compose run --rm hermes model`.

**Atenção:** no backend `hermes` as tools rodam **dentro do container** — ele
navega na web, mexe em arquivos e roda comandos no Linux do container, não no
seu Windows. Para ações no seu PC ("abre o Spotify"), use `BACKEND=ollama` ou
`openai`, que usam as tools locais deste projeto.

## Segurança

A tool `run_powershell` permite que o LLM execute comandos no seu computador.
Ela vem **desabilitada** (`ALLOW_SHELL=false`). Habilite por sua conta e risco.
