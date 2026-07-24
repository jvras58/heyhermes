"""Loop principal: wake word -> gravação -> transcrição -> agente -> voz."""

import logging
import threading
from collections.abc import Iterator

import numpy as np

from heyhermes.agent.actions import HostActions
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


def _run_barge_in_listener(wake: WakeWordListener, stop_event: threading.Event) -> None:
    detected = wake.listen(stop_event=stop_event)
    if detected is not None and not stop_event.is_set():
        log.info("Barge-in ativado! Interrompendo a fala…")
        stop_event.set()


def _speak(tts: TextToSpeech, answer: Iterator[str], wake: WakeWordListener) -> bool:
    """Fala a resposta enquanto escuta a wake word. Retorna True se foi interrompida.

    A fala e o barge-in rodam em paralelo: quem detectar a wake word primeiro
    seta o `stop_event` e corta o áudio no meio.
    """
    stop_event = threading.Event()
    tts_thread = threading.Thread(
        target=tts.say_stream, args=(answer, stop_event), daemon=True
    )
    barge_in_thread = threading.Thread(
        target=_run_barge_in_listener, args=(wake, stop_event), daemon=True
    )
    tts_thread.start()
    barge_in_thread.start()
    tts_thread.join()
    interrupted = stop_event.is_set()  # se já está setado, foi o barge-in
    stop_event.set()  # encerra o listener quando a fala termina naturalmente
    barge_in_thread.join(timeout=1.0)
    return interrupted


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
            if not _conversation(settings, stt, tts, brain, wake):
                break
            log.info("Voltando a dormir; aguardando wake word…")
            wake.cooldown()
    except KeyboardInterrupt:
        log.info("Encerrando…")


def _conversation(
    settings,
    stt: SpeechToText,
    tts: TextToSpeech,
    brain: Brain,
    wake: WakeWordListener,
) -> bool:
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

        actions = HostActions(settings)
        answer = actions.filter_stream(brain.ask_stream(command))
        # só abre navegador/relatório se a resposta terminou (não foi interrompida)
        if not _speak(tts, answer, wake):
            actions.execute()
        if not settings.follow_up:
            return True


if __name__ == "__main__":
    main()
