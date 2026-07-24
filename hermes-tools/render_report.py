#!/usr/bin/env python3
"""Renderiza um relatório HTML a partir de linhas em JSON — SEM tocar no banco.

Na arquitetura com MCP, quem consulta o banco é o servidor DBHub (read-only,
container isolado). O agente recebe as linhas pela tool `execute_sql` e passa
esse resultado para cá só para virar um HTML bonito (tabela + gráfico). Assim
este script — que roda no lado do agente — não tem nenhum acesso a credencial
ou banco.

Entrada (JSON), via --in ARQUIVO ou stdin. Aceita qualquer um destes formatos:
  - lista de objetos:   [{"categoria":"X","total":10}, ...]
  - {"columns":[...], "rows":[[...], ...]}
  - {"rows":[{...}, ...]}

Uso:
  uv run /hermes-tools/render_report.py --title "Vendas" --out /reports/v.html \
      --in /reports/.dados.json
  echo '[{"a":1}]' | uv run /hermes-tools/render_report.py --title "T" --out /reports/t.html
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime
from pathlib import Path

MAX_ROWS_HTML = 500
PREVIEW_ROWS = 5


def _columns_from_dicts(rows: list[dict]) -> list[str]:
    """União das chaves de todas as linhas, na ordem em que aparecem."""
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    return columns


def _to_table(raw: list, columns: list[str] | None) -> tuple[list[str], list[tuple]]:
    """Converte linhas (objetos ou sequências) em (colunas, tuplas)."""
    if raw and isinstance(raw[0], dict):
        columns = columns or _columns_from_dicts(raw)
        return columns, [tuple(row.get(c) for c in columns) for row in raw]
    rows = [tuple(r) if isinstance(r, (list, tuple)) else (r,) for r in raw]
    width = len(rows[0]) if rows else 0
    return list(columns or [f"col{i + 1}" for i in range(width)]), rows


def normalize(data) -> tuple[list[str], list[tuple]]:
    """Aceita os vários formatos de saída de uma consulta e devolve (colunas, linhas)."""
    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(data, dict) and "rows" in data:
        return _to_table(data["rows"], data.get("columns"))
    if isinstance(data, list):
        return _to_table(data, None)
    raise ValueError("JSON não reconhecido: envie uma lista de objetos ou {columns, rows}.")

def _looks_numeric(values: list) -> bool:
    seen = False
    for v in values:
        if v is None:
            continue
        try:
            float(v)
            seen = True
        except (TypeError, ValueError):
            return False
    return seen


def _fmt(value) -> str:
    if isinstance(value, bool):
        return "sim" if value else "não"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        f = float(value)
        if f.is_integer():
            return f"{int(f):,}".replace(",", ".")
        return f"{f:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return html.escape(str(value))


def _bar_chart(columns: list[str], rows: list[tuple]) -> str:
    """Gráfico de barras simples (CSS) quando os dados são rótulo + número."""
    if len(columns) != 2 or not rows:
        return ""
    labels = [r[0] for r in rows]
    raw = [r[1] for r in rows]
    if not _looks_numeric(raw):
        return ""
    values = [float(v) if v is not None else 0.0 for v in raw]
    top = sorted(zip(labels, values, strict=False), key=lambda x: x[1], reverse=True)[:20]
    biggest = max((v for _, v in top), default=0.0) or 1.0
    bars = []
    for label, value in top:
        pct = max(0.0, value / biggest * 100.0)
        bars.append(
            f'<div class="bar-row"><span class="bar-label">{html.escape(str(label))}</span>'
            f'<span class="bar-track"><span class="bar-fill" style="width:{pct:.1f}%">'
            f"</span></span>"
            f'<span class="bar-value">{_fmt(value)}</span></div>'
        )
    heading = f"{html.escape(columns[1])} por {html.escape(columns[0])}"
    return f'<section class="chart"><h2>{heading}</h2>{"".join(bars)}</section>'


def render_html(title: str, columns: list[str], rows: list[tuple]) -> str:
    generated = datetime.now().strftime("%d/%m/%Y %H:%M")
    total = len(rows)
    shown = rows[:MAX_ROWS_HTML]

    head = "".join(f"<th>{html.escape(c)}</th>" for c in columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{_fmt(v) if v is not None else '—'}</td>" for v in row) + "</tr>"
        for row in shown
    )
    truncated = (
        f'<p class="note">Mostrando as primeiras {MAX_ROWS_HTML} de {total} linhas.</p>'
        if total > MAX_ROWS_HTML
        else ""
    )
    chart = _bar_chart(columns, shown)

    return f"""
    <!doctype html>
    <html lang="pt-BR">
    <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{html.escape(title)}</title>
    <style>
    :root {{
        --bg:#f7f7f8; --card:#fff; --ink:#1a1a1e; --muted:#6b6b76; --line:#e6e6ea;
        --accent:#6d5efc; --accent-soft:#efeaff; --head:#f0f0f3;
    }}
    @media (prefers-color-scheme: dark) {{
        :root {{
        --bg:#141418; --card:#1c1c22; --ink:#ececf1; --muted:#9a9aa6; --line:#2b2b33;
        --accent:#9b8dff; --accent-soft:#26233a; --head:#22222a;
        }}
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; padding:32px 20px; background:var(--bg); color:var(--ink);
        font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }}
    .wrap {{ max-width:960px; margin:0 auto; }}
    header {{ margin-bottom:24px; }}
    h1 {{ font-size:1.6rem; margin:0 0 4px; }}
    .sub {{ color:var(--muted); font-size:.9rem; }}
    .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
        padding:20px; margin-bottom:20px; box-shadow:0 1px 3px rgba(0,0,0,.04); }}
    h2 {{ font-size:1.05rem; margin:0 0 14px; }}
    .table-scroll {{ overflow-x:auto; }}
    table {{ border-collapse:collapse; width:100%; font-size:.92rem; }}
    th,td {{ text-align:left; padding:9px 12px; border-bottom:1px solid var(--line);
        white-space:nowrap; }}
    th {{ background:var(--head); font-weight:600; position:sticky; top:0; }}
    tr:hover td {{ background:var(--accent-soft); }}
    .note {{ color:var(--muted); font-size:.85rem; margin:10px 2px 0; }}
    .bar-row {{ display:grid; grid-template-columns:minmax(90px,26%) 1fr auto; align-items:center;
        gap:12px; margin:7px 0; font-size:.9rem; }}
    .bar-label {{ color:var(--muted); overflow:hidden; text-overflow:ellipsis; }}
    .bar-track {{ background:var(--accent-soft); border-radius:99px; height:12px; }}
    .bar-fill {{ display:block; height:100%; border-radius:99px; background:var(--accent); }}
    .bar-value {{ font-variant-numeric:tabular-nums; font-weight:600; }}
    footer {{ color:var(--muted); font-size:.8rem; text-align:center; margin-top:8px; }}
    </style>
    </head>
    <body>
    <div class="wrap">
        <header>
        <h1>{html.escape(title)}</h1>
        <div class="sub">Gerado em {generated} · {total} linha(s) · HeyHermes 🪽</div>
        </header>
        {chart}
        <div class="card">
        <h2>Dados</h2>
        <div class="table-scroll">
            <table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>
        </div>
        {truncated}
        </div>
        <footer>Relatório somente-leitura gerado automaticamente pelo agente.</footer>
    </div>
    </body>
    </html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Renderiza linhas JSON em um relatório HTML.")
    parser.add_argument("--title", default="Relatório")
    parser.add_argument("--out", default="/reports/relatorio.html")
    parser.add_argument("--in", dest="infile", help="arquivo JSON de entrada (padrão: stdin)")
    args = parser.parse_args()

    text = Path(args.infile).read_text(encoding="utf-8") if args.infile else sys.stdin.read()
    if not text.strip():
        sys.exit("Erro: nenhuma entrada JSON (use --in ARQUIVO ou envie por stdin).")
    try:
        columns, rows = normalize(json.loads(text))
    except (json.JSONDecodeError, ValueError) as exc:
        sys.exit(f"Erro ao ler o JSON: {exc}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(args.title, columns, rows), encoding="utf-8")

    print(f"OK: relatório gerado em {out}")
    print(f"Linhas: {len(rows)} | Colunas: {', '.join(columns) or '(nenhuma)'}")
    if rows:
        print("Prévia:")
        for row in rows[:PREVIEW_ROWS]:
            print("  " + " · ".join("—" if v is None else str(v) for v in row))
    print(f"\nAbra na tela do usuário com: [[ABRIR_RELATORIO {out.name}]]")


if __name__ == "__main__":
    main()
