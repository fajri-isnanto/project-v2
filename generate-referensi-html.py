#!/usr/bin/env python3
"""Generator REFERENSI-INSTALASI.html dari REFERENSI-INSTALASI.md (bkpm-ha-v2).

Usage: python3 generate-referensi-html.py
Output: REFERENSI-INSTALASI.html (di folder yang sama dengan script ini)

Mendukung subset markdown yang dipakai di dokumen ini:
  # / ## / ### heading, tabel, blockquote (>) -> div.note, fenced code block,
  paragraph, inline `code`, **bold**, escape HTML otomatis.
"""
import html
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
MD = BASE / "REFERENSI-INSTALASI.md"
HTML_OUT = BASE / "REFERENSI-INSTALASI.html"

CSS = """\
  body { font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; background:#f5f6f8; color:#1a202c; margin:0; padding:24px; }
  .wrap { max-width:1100px; margin:0 auto; }
  h1 { font-size:22px; margin:0 0 4px; }
  .sub { color:#4a5568; font-size:13px; margin-bottom:24px; }
  h2 { font-size:16px; margin:28px 0 10px; padding-top:16px; border-top:2px solid #e2e8f0; }
  h3 { font-size:13.5px; margin:18px 0 8px; color:#2d3748; }
  table { width:100%; border-collapse:collapse; background:#fff; border:1px solid #e2e8f0; border-radius:8px; overflow:hidden; font-size:13px; margin-bottom:8px; }
  th { background:#f1f5f9; text-align:left; padding:8px 12px; font-weight:600; color:#334155; border-bottom:1px solid #e2e8f0; white-space:nowrap; }
  td { padding:7px 12px; border-bottom:1px solid #f1f5f9; vertical-align:top; }
  tr:last-child td { border-bottom:none; }
  tr:nth-child(even) td { background:#f8fafc; }
  code { background:#eef2f7; padding:1px 6px; border-radius:4px; font-size:12px; font-family:ui-monospace, SFMono-Regular, Menlo, monospace; color:#0f172a; }
  pre { background:#0f172a; color:#e2e8f0; padding:14px 16px; border-radius:8px; font-size:12.5px; line-height:1.6; overflow-x:auto; font-family:ui-monospace, SFMono-Regular, Menlo, monospace; }
  .note { background:#fffbeb; border:1px solid #fcd34d; border-radius:8px; padding:8px 14px; font-size:12.5px; color:#78350f; margin:8px 0 16px; }
  .foot { color:#94a3b8; font-size:12px; margin-top:28px; }
"""


def inline(text: str) -> str:
    """Escape HTML dulu, baru terapkan `code` dan **bold**."""
    t = html.escape(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t


def render_table(rows: list[str]) -> str:
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    # buang baris pemisah (|---|)
    cells = [r for r in cells if not all(re.fullmatch(r":?-+:?", c) for c in r)]
    head, body = cells[0], cells[1:]
    out = ["  <table>", "    <tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr>"]
    for row in body:
        out.append("    <tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>")
    out.append("  </table>")
    return "\n".join(out)


def main() -> None:
    lines = MD.read_text().splitlines()
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        s = line.strip()

        if not s:
            i += 1
            continue
        if s == "---":
            i += 1
            continue
        if s.startswith("# "):
            out.append(f"  <h1>{inline(s[2:])}</h1>")
            i += 1
            continue
        if s.startswith("## "):
            out.append(f"  <h2>{inline(s[3:])}</h2>")
            i += 1
            continue
        if s.startswith("### "):
            out.append(f"  <h3>{inline(s[4:])}</h3>")
            i += 1
            continue
        if s.startswith("```"):
            block = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1  # lewati penutup
            out.append(f"  <pre>{html.escape(chr(10).join(block))}</pre>")
            continue
        if s.startswith("|"):
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            out.append(render_table(rows))
            continue
        if s.startswith(">"):
            block = []
            while i < n and lines[i].strip().startswith(">"):
                block.append(lines[i].strip().lstrip("> ").strip())
                i += 1
            out.append(f"  <div class=\"note\">{inline(' '.join(block))}</div>")
            continue

        # paragraph biasa
        if s.startswith("*Dibuat") or s.startswith("Dibuat:"):
            out.append(f"  <p class=\"foot\">{inline(s.strip('*'))}</p>")
        else:
            out.append(f"  <p>{inline(s)}</p>")
        i += 1

    doc = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Referensi Instalasi — BKPM HA Stack</title>
<style>
{CSS}</style>
</head>
<body>
<div class="wrap">
{chr(10).join(out)}
</div>
</body>
</html>
"""
    HTML_OUT.write_text(doc)
    print(f"OK: {HTML_OUT} ({HTML_OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    sys.exit(main())
