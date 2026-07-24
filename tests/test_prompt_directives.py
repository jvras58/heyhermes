"""Trava de consistência: as diretivas ensinadas no prompt == as que o parser lê.

O protocolo `[[ABRIR_...]]` vive em dois lugares: o texto do SYSTEM_PROMPT
(core/config.py) ensina o agente, e o parser (agent/actions.py) as reconhece.
Renomear uma sem a outra silenciosamente quebraria o recurso; estes testes
falham na hora se isso acontecer.
"""

from __future__ import annotations

import re

from heyhermes.agent import actions
from heyhermes.agent.actions import HostActions
from heyhermes.core.config import SYSTEM_PROMPT, Settings

# verbos ensinados no prompt, ex.: [[ABRIR_SITE ...]] -> "SITE"
_PROMPT_VERBS = re.compile(r"\[\[\s*ABRIR_([A-Z]+)")
# ocorrências completas de diretiva no prompt, para passar pelo parser de verdade
_PROMPT_DIRECTIVES = re.compile(r"\[\[\s*ABRIR_[A-Z]+[^\]]*\]\]")


def test_prompt_and_parser_know_the_same_verbs():
    verbs_in_prompt = set(_PROMPT_VERBS.findall(SYSTEM_PROMPT))
    assert verbs_in_prompt, "o SYSTEM_PROMPT deveria ensinar diretivas [[ABRIR_...]]"
    # exatamente os mesmos verbos dos dois lados — pega rename em qualquer direção
    assert verbs_in_prompt == set(actions._KINDS)


def test_every_directive_example_in_prompt_is_parsed():
    examples = _PROMPT_DIRECTIVES.findall(SYSTEM_PROMPT)
    assert examples, "o prompt deveria conter exemplos de diretiva"

    host = HostActions(Settings(_env_file=None))
    for example in examples:
        host.actions.clear()
        host._record(example)
        assert host.actions, f"parser não reconheceu a diretiva do prompt: {example!r}"
        kind = host.actions[0][0]
        assert kind in actions._KINDS.values()
