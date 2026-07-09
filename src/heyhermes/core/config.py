"""Central de configurações com Pydantic-Settings.

Tudo pode ser sobrescrito via variáveis de ambiente ou arquivo .env na raiz
do projeto (ex.: WHISPER_MODEL=base, WAKE_THRESHOLD=0.6).
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# raiz do repositório (src/heyhermes/core/config.py -> 3 níveis acima)
BASE_DIR = Path(__file__).resolve().parents[3]


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

    system_prompt: str = (
        "Você é Hermes, um assistente de voz pessoal no estilo Jarvis. "
        "Responda sempre em português do Brasil, de forma curta e natural, "
        "como uma fala — sem markdown, sem listas, sem emojis. "
        "Use as ferramentas disponíveis quando o pedido exigir uma ação."
    )
    # histórico máximo de mensagens mantido entre turnos
    max_history: int = 20

    # ------------------------------------------------------------------ comandos pré-definidos
    exit_commands: list[str] = ["desligar", "encerrar", "pode dormir", "tchau hermes"]
    cancel_commands: list[str] = ["cancelar", "deixa pra lá", "nada não"]


settings = Settings()
