"""Testes do HostActions: filtro de stream e execução das ações no host."""

from __future__ import annotations

import pytest

from heyhermes.agent.actions import HostActions


def _chars(text: str) -> list[str]:
    """Simula o pior caso de streaming: um caractere por token."""
    return list(text)


# --------------------------------------------------------------- filter_stream
# (descrição, tokens, fala esperada, ações esperadas)
FILTER_CASES = [
    (
        "site-simples",
        _chars("Abrindo o site.\n[[ABRIR_SITE https://github.com]]"),
        "Abrindo o site.\n",
        [("site", "https://github.com")],
    ),
    (
        "relatorio-simples",
        _chars("Aqui está o relatório.\n[[ABRIR_RELATORIO vendas-julho.html]]"),
        "Aqui está o relatório.\n",
        [("report", "vendas-julho.html")],
    ),
    (
        "marcador-quebrado-entre-tokens",
        ["Oi ", "[", "[ABRIR_", "SITE htt", "p://x.com]", "] tchau"],
        "Oi  tchau",
        [("site", "http://x.com")],
    ),
    (
        "colchete-solto-nao-e-diretiva",
        _chars("custo [reais] alto"),
        "custo [reais] alto",
        [],
    ),
    (
        "sem-diretiva",
        _chars("Tudo certo por aqui."),
        "Tudo certo por aqui.",
        [],
    ),
    (
        "relatorio-com-aspas",
        _chars('pronto [[ABRIR_RELATORIO "meu-rel.html"]]'),
        "pronto ",
        [("report", "meu-rel.html")],
    ),
    (
        "dois-marcadores",
        _chars("veja [[ABRIR_RELATORIO a.html]] e [[ABRIR_SITE https://y.com]] fim"),
        "veja  e  fim",
        [("report", "a.html"), ("site", "https://y.com")],
    ),
]


@pytest.mark.parametrize(
    "tokens,spoken,expected",
    [case[1:] for case in FILTER_CASES],
    ids=[case[0] for case in FILTER_CASES],
)
def test_filter_stream(host_actions: HostActions, tokens, spoken, expected):
    out = "".join(host_actions.filter_stream(iter(tokens)))
    assert out == spoken  # a diretiva nunca é falada
    assert host_actions.actions == expected


# --------------------------------------------------------------------- execute
def test_execute_opens_existing_report(host_actions, settings, opened):
    report = settings.reports_dir / "rel.html"
    report.write_text("<h1>ok</h1>", encoding="utf-8")

    host_actions.actions = [("report", "rel.html")]
    host_actions.execute()

    assert len(opened) == 1
    assert opened[0].startswith("file://")
    assert opened[0].endswith("rel.html")


def test_execute_blocks_path_traversal(host_actions, opened):
    host_actions.actions = [("report", "../../../windows/system32/x.html")]
    host_actions.execute()
    assert opened == []


def test_execute_ignores_missing_report(host_actions, opened):
    host_actions.actions = [("report", "nao-existe.html")]
    host_actions.execute()
    assert opened == []


def test_execute_opens_http_site(host_actions, opened):
    host_actions.actions = [("site", "https://nousresearch.com")]
    host_actions.execute()
    assert opened == ["https://nousresearch.com"]


def test_execute_ignores_non_http_scheme(host_actions, opened):
    host_actions.actions = [("site", "javascript:alert(1)")]
    host_actions.execute()
    assert opened == []


def test_disabled_host_actions_ignores_everything(make_settings, opened):
    settings = make_settings(enable_host_actions=False)
    actions = HostActions(settings)
    actions.actions = [("report", "x.html"), ("site", "https://x.com")]
    actions.execute()
    assert opened == []


def test_allow_open_url_false_blocks_sites(make_settings, opened):
    settings = make_settings(allow_open_url=False)
    actions = HostActions(settings)
    actions.actions = [("site", "https://x.com")]
    actions.execute()
    assert opened == []


def test_execute_clears_actions(host_actions, opened):
    host_actions.actions = [("site", "https://x.com")]
    host_actions.execute()
    assert host_actions.actions == []  # não reexecuta se chamado de novo
