"""Loop principal: wake word -> gravação -> transcrição -> agente -> voz."""

import logging

import numpy as np

from heyhermes.agent.brain import Brain
from heyhermes.audio.mic import MicStream
from heyhermes.audio.stt import SpeechToText
from heyhermes.audio.tts import TextToSpeech
from heyhermes.audio.wake_word import WakeWordListener
from heyhermes.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s")
log = logging.getLogger("heyhermes")


def _matches(text: str, phrases: list[str]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def _check_microphone() -> None:
    """Mede meio segundo de ambiente e avisa se o microfone parece morto."""
    with MicStream(settings, frame_samples=1280) as mic:
        ambient = np.concatenate([mic.read() for _ in range(6)])
    rms = float(np.sqrt(np.mean(ambient.astype(np.float64) ** 2)))
    log.info("Nível ambiente do microfone: RMS %.0f", rms)
    if rms < 10:
        log.warning(
            "Microfone quase sem sinal! Confira o mic padrão do Windows ou defina "
            "INPUT_DEVICE no .env (liste os dispositivos com: uv run python -m sounddevice)."
        )


def main() -> None:
    log.info("Inicializando HeyHermes (hermes-agent em %s)…", settings.hermes_base_url)
    tts = TextToSpeech(settings)
    stt = SpeechToText(settings)
    wake = WakeWordListener(settings)
    brain = Brain(settings)
    _check_microphone()

    tts.say("Hermes online.")
    log.info("Aguardando wake word (%s)…", ", ".join(settings.wake_words))

    try:
        while True:
            wake.listen()
            tts.say(settings.ack_phrase)
            if not _conversation(settings, stt, tts, brain):
                break
            log.info("Voltando a dormir; aguardando wake word…")
            wake.cooldown()
    except KeyboardInterrupt:
        log.info("Encerrando…")


def _conversation(settings, stt: SpeechToText, tts: TextToSpeech, brain: Brain) -> bool:
    """Conduz uma conversa até o usuário silenciar, cancelar ou encerrar.

    No modo conversa (FOLLOW_UP=true), após cada resposta o assistente volta a
    escutar sem exigir a wake word de novo. Retorna False se for para desligar.
    """
    while True:
        command = stt.listen_command()
        if not command:
            return True
        if _matches(command, settings.exit_commands):
            tts.say("Até logo!")
            return False
        if _matches(command, settings.cancel_commands):
            tts.say("Tá bom.")
            return True

        answer = brain.ask(command)
        tts.say(answer or "Feito.")
        if not settings.follow_up:
            return True


if __name__ == "__main__":
    main()
