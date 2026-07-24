"""Central de configurações com Pydantic-Settings.

Tudo pode ser sobrescrito via variáveis de ambiente ou arquivo .env na raiz
do projeto (ex.: WHISPER_MODEL=base, WAKE_THRESHOLD=0.6).
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# raiz do repositório (src/heyhermes/core/config.py -> 3 níveis acima)
BASE_DIR = Path(__file__).resolve().parents[3]

# Persona + procedimento das ações no host. As diretivas [[...]] descritas aqui
# são interpretadas por agent/actions.py — mantenha os nomes em sincronia.
SYSTEM_PROMPT = """\
Você é Hermes, um assistente de voz pessoal no estilo Jarvis. Responda sempre
em português do Brasil, de forma curta e natural, como uma fala — sem markdown,
sem listas, sem emojis. Use as ferramentas disponíveis quando o pedido exigir
uma ação.

Você pode agir no computador do usuário emitindo diretivas no texto. Cada
diretiva vai numa LINHA ISOLADA e não é falada — antes dela, diga uma frase
curta em voz alta.

1) ABRIR UM SITE no navegador do usuário: escreva
   [[ABRIR_SITE https://exemplo.com]]
   Use isto (não o navegador interno das suas tools) quando ele pedir para
   abrir/ver um site.

2) RELATÓRIOS do banco do usuário. Você tem ferramentas MCP somente-leitura:
   'search_objects' (procura tabelas/colunas) e 'execute_sql' (roda um SELECT).
   Fluxo:
   a) use search_objects para descobrir as tabelas e colunas;
   b) rode um SELECT com execute_sql;
   c) salve o resultado num arquivo como um ARRAY JSON de objetos — ou seja
      [{"coluna": valor, ...}, ...], não JSONL — e gere o relatório (nome do
      arquivo em minúsculas-com-hifens):
      printf '%s' '<json>' > /reports/.dados.json && uv run \
/hermes-tools/render_report.py --title "Título" --out /reports/nome.html \
--in /reports/.dados.json
   d) então emita, em linha isolada, [[ABRIR_RELATORIO nome.html]] e fale um
      resumo de 1 ou 2 frases do que os dados mostram.
   Só faça SELECT. Se a consulta falhar, use search_objects de novo e corrija
   os nomes das tabelas/colunas.
"""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------ wake word
    # Nomes de modelos pré-treinados do openWakeWord (ex.: "hey_jarvis") ou
    # caminho para um .onnx customizado (ex.: treinado para "hey hermes").
    wake_words: list[str] = ["hey_jarvis"]
    wake_threshold: float = 0.5
    # segundos ignorando o microfone logo após uma detecção (evita disparo duplo)
    wake_cooldown: float = 2.0
    frames_samples: int = 1280  # 80 ms a 16 kHz (openWakeWord)

    # ------------------------------------------------------------------ áudio / STT
    sample_rate: int = 16_000
    # índice do dispositivo de entrada (None = padrão do sistema);
    # liste com: uv run python -m sounddevice
    input_device: int | None = None
    # ganho de software aplicado à captura (para microfones fracos);
    # se aumentar, aumente SILENCE_THRESHOLD na mesma proporção
    input_gain: float = 1.0
    whisper_model: str = "small"  # tiny | base | small | medium | large-v3
    whisper_device: str = "cpu"  # cpu | cuda
    whisper_compute_type: str = "int8"  # int8 (cpu) | float16 (gpu)
    language: str = "pt"
    # detecção de fim de fala por energia
    silence_threshold: float = 300.0  # RMS mínimo para considerar "falando"
    silence_seconds: float = 1.2  # silêncio contínuo que encerra a gravação
    max_command_seconds: float = 15.0  # duração máxima de um comando
    # se ninguém começar a falar nesse tempo, desiste da gravação
    speech_start_timeout: float = 6.0
    # modo conversa: após responder, volta a escutar sem exigir a wake word
    follow_up: bool = True

    # ------------------------------------------------------------------ TTS (Piper)
    piper_voice: str = "pt_BR-faber-medium"
    piper_dir: Path = BASE_DIR / "models" / "piper"
    ack_phrase: str = "Sim?"  # resposta curta ao acordar

    # ------------------------------------------------------------------ cérebro
    # hermes-agent (NousResearch) rodando via Docker — ver compose.yml.
    # A API é OpenAI-compatível; as tools/memória rodam do lado do hermes.
    # O modelo/provedor do LLM é configurado no próprio hermes (ver README).
    hermes_base_url: str = "http://localhost:8642/v1"
    hermes_api_key: str = "change-me-local-dev"
    hermes_model: str = "hermes-agent"
    hermes_timeout: float = 300.0  # o agente pode demorar (executa tools)

    system_prompt: str = SYSTEM_PROMPT
    # histórico máximo de mensagens mantido entre turnos
    max_history: int = 20

    # ------------------------------------------------------------------ ações no host
    # onde o agente grava relatórios (montado como /reports no container);
    # o heyhermes abre esses arquivos no navegador do Windows
    reports_dir: Path = BASE_DIR / "reports"
    # liga/desliga a ponte de ações (abrir navegador/relatório no host)
    enable_host_actions: bool = True
    # permite [[ABRIR_SITE ...]] abrir URLs no navegador padrão
    allow_open_url: bool = True

    # ------------------------------------------------------------------ comandos pré-definidos
    exit_commands: list[str] = ["desligar", "encerrar", "pode dormir", "tchau hermes"]
    cancel_commands: list[str] = ["cancelar", "deixa pra lá", "nada não"]


settings = Settings()
