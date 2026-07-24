"""Ponte de ações do host: abrir navegador / relatório no computador do usuário.

As tools do hermes rodam DENTRO do container (sandbox), então o agente não
consegue abrir o navegador do Windows nem mostrar um arquivo na tela. Para
isso, ele emite diretivas no texto da resposta:

    [[ABRIR_SITE https://exemplo.com]]
    [[ABRIR_RELATORIO vendas-julho.html]]

`HostActions` filtra essas diretivas do stream (para o Piper não falá-las),
coleta o que fazer e, quando a fala termina, executa no host: abre a URL no
navegador padrão ou o relatório gerado (de ./reports) via file://.
"""

from __future__ import annotations

import logging
import re
import webbrowser
from collections.abc import Iterable, Iterator
from pathlib import Path

from heyhermes.core.config import Settings

log = logging.getLogger(__name__)

# As diretivas são ensinadas ao agente no SYSTEM_PROMPT (core/config.py) —
# mantenha os nomes em sincronia com o texto de lá.
_DIRECTIVE_RE = re.compile(r"\[\[\s*ABRIR_(SITE|RELATORIO)\s+(.+?)\s*\]\]", re.IGNORECASE)
_KINDS = {"SITE": "site", "RELATORIO": "report"}


class HostActions:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.actions: list[tuple[str, str]] = []

    def filter_stream(self, tokens: Iterable[str]) -> Iterator[str]:
        """Repassa o texto para a fala, mas engole as diretivas `[[...]]`.

        Máquina de estados por caractere: fora de uma diretiva o texto flui
        normalmente; ao ver `[[` segura tudo até o `]]`, registra a ação e não
        fala nada daquele trecho. Assim o streaming continua responsivo.
        """
        buf = ""
        holding = False
        for token in tokens:
            buf += token
            while buf:
                if not holding:
                    i = buf.find("[")
                    if i == -1:
                        yield buf
                        buf = ""
                        break
                    if i > 0:
                        yield buf[:i]
                        buf = buf[i:]
                    if len(buf) < 2:
                        break
                    if buf[1] == "[":
                        holding = True
                        continue
                    yield buf[0]
                    buf = buf[1:]
                    continue
                j = buf.find("]]")
                if j == -1:
                    break
                self._record(buf[: j + 2])
                buf = buf[j + 2 :]
                holding = False
        if buf and not holding:
            yield buf
        elif buf and holding:
            self._record(buf)

    def _record(self, marker: str) -> None:
        """Registra a ação de um `[[...]]` completo; ignora o que não casar."""
        m = _DIRECTIVE_RE.search(marker)
        if m:
            self.actions.append((_KINDS[m.group(1).upper()], m.group(2).strip("\"'")))

    def execute(self) -> None:
        if not self.settings.enable_host_actions:
            if self.actions:
                log.info("Ações do host desativadas; ignorando %d ação(ões).", len(self.actions))
            self.actions.clear()
            return
        for kind, value in self.actions:
            if kind == "site":
                self._open_url(value)
            elif kind == "report":
                self._open_report(value)
        self.actions.clear()

    def _open_report(self, name: str) -> None:
        safe = self.settings.reports_dir / Path(name).name
        reports_root = self.settings.reports_dir.resolve()
        path = safe.resolve()
        if reports_root not in path.parents:
            log.warning("Relatório fora de ./reports, ignorado: %r", name)
            return
        if not path.exists():
            log.warning("Relatório não encontrado: %s", path)
            return
        log.info("Abrindo relatório no navegador: %s", path)
        self._open(path.as_uri())

    def _open_url(self, url: str) -> None:
        if not self.settings.allow_open_url:
            log.info("Abrir sites está desativado (ALLOW_OPEN_URL=false); ignorando %s", url)
            return
        if not re.match(r"^https?://", url, re.IGNORECASE):
            log.warning("URL sem http/https, ignorada: %r", url)
            return
        log.info("Abrindo site no navegador: %s", url)
        self._open(url)

    @staticmethod
    def _open(target: str) -> None:
        try:
            webbrowser.open(target)
        except Exception:
            log.exception("Falha ao abrir no navegador")
