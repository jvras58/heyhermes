"""Loop de escuta da wake word com openWakeWord.

Usa o modelo pré-treinado "hey_jarvis" por padrão. Para "hey hermes" é preciso
treinar um modelo customizado (notebook oficial do openWakeWord) e apontar o
caminho do .onnx em WAKE_WORDS no .env.
"""

import logging
import threading
import time
from pathlib import Path

from openwakeword.model import Model

from heyhermes.audio.mic import MicStream
from heyhermes.core.config import Settings

log = logging.getLogger(__name__)


def _ensure_pretrained_models(names: list[str]) -> None:
    """Baixa os modelos pré-treinados do openWakeWord na primeira execução."""
    pretrained = [n for n in names if not n.endswith(".onnx")]
    if not pretrained:
        return
    try:
        from openwakeword.utils import download_models

        download_models()
    except Exception as exc:
        log.warning("Não foi possível baixar modelos do openWakeWord: %s", exc)


def _resolve_model(name: str) -> str:
    """Aceita nome pré-treinado do openWakeWord ou caminho de um .onnx customizado."""
    if not name.endswith(".onnx"):
        return name
    path = Path(name)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        raise FileNotFoundError(f"Modelo de wake word não encontrado: {path}")
    return str(path)


class WakeWordListener:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        _ensure_pretrained_models(settings.wake_words)
        models = [_resolve_model(name) for name in settings.wake_words]
        self.model = Model(wakeword_models=models, inference_framework="onnx")

    def listen(self, stop_event: threading.Event | None = None) -> str | None:
        """Bloqueia até detectar uma wake word ou até um stop_event ser acionado."""
        s = self.settings
        self.model.reset()
        with MicStream(s, frame_samples=s.frames_samples) as mic:
            while True:
                if stop_event is not None and stop_event.is_set():
                    return None
                self.model.predict(mic.read())
                if stop_event is not None and stop_event.is_set():
                    return None
                for name, buffer in self.model.prediction_buffer.items():
                    if buffer and buffer[-1] >= s.wake_threshold:
                        log.info("Wake word detectada: %s (%.2f)", name, buffer[-1])
                        self.model.reset()
                        return name

    def cooldown(self) -> None:
        time.sleep(self.settings.wake_cooldown)
