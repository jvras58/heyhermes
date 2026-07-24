"""Testes do renderizador de relatórios (hermes-tools/render_report.py)."""

from __future__ import annotations

import pytest


# ------------------------------------------------------------------- normalize
def test_normalize_list_of_dicts(render_report):
    cols, rows = render_report.normalize([{"a": 1, "b": 2}, {"a": 3, "b": 4}])
    assert cols == ["a", "b"]
    assert rows == [(1, 2), (3, 4)]


def test_normalize_columns_and_rows(render_report):
    cols, rows = render_report.normalize({"columns": ["p", "q"], "rows": [["x", 1]]})
    assert cols == ["p", "q"]
    assert rows == [("x", 1)]


def test_normalize_rows_of_dicts(render_report):
    cols, rows = render_report.normalize({"rows": [{"a": 1}, {"a": 2}]})
    assert cols == ["a"]
    assert rows == [(1,), (2,)]


def test_normalize_ragged_keys_use_union(render_report):
    # chaves irregulares: a união preenche os buracos com None (era o bug antigo)
    cols, rows = render_report.normalize([{"a": 1}, {"a": 2, "b": 9}])
    assert cols == ["a", "b"]
    assert rows == [(1, None), (2, 9)]


def test_normalize_accepts_json_string(render_report):
    cols, rows = render_report.normalize('[{"a": 1}]')
    assert cols == ["a"]
    assert rows == [(1,)]


def test_normalize_rejects_unknown_shape(render_report):
    with pytest.raises(ValueError, match="JSON não reconhecido"):
        render_report.normalize(42)


# ----------------------------------------------------------------- render_html
def test_render_html_table_chart_and_ptbr_number(render_report):
    cols, rows = render_report.normalize(
        [{"categoria": "Eletrônicos", "total": 31050}, {"categoria": "Móveis", "total": 13849.2}]
    )
    html = render_report.render_html("Faturamento", cols, rows)

    assert "<table>" in html
    assert "Eletrônicos" in html  # UTF-8 preservado
    # 2 colunas (rótulo + número) => a <section class="chart"> é gerada
    assert '<section class="chart">' in html
    assert "31.050" in html  # número formatado em pt-BR


def test_render_html_no_chart_when_not_label_plus_number(render_report):
    cols, rows = render_report.normalize([{"nome": "Ana", "cidade": "Recife"}])
    html = render_report.render_html("Clientes", cols, rows)
    # a classe .bar-fill existe sempre no <style>; o que indica gráfico é a <section>
    assert '<section class="chart">' not in html


def test_render_html_escapes_html_in_values(render_report):
    cols, rows = render_report.normalize([{"x": "<script>alert(1)</script>"}])
    html = render_report.render_html("XSS", cols, rows)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
