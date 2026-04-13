from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "paper"
SITE_PUBLIC = ROOT / "site" / "public"
DISPLAY_PUBLIC_DIR = SITE_PUBLIC / "paper-assets" / "paper-display"
BUILD_DIR = PAPER_DIR / "_paper_display_build"
MANIFEST_PATH = ROOT / "site" / "src" / "generated" / "paper" / "paper_display_manifest.json"
TEX_SOURCE = PAPER_DIR / "research_allocation_paper.tex"
TECTONIC = shutil.which("tectonic") or "/opt/homebrew/bin/tectonic"
PDFTOCAIRO = shutil.which("pdftocairo") or "/opt/homebrew/bin/pdftocairo"


ENV_PATTERN = re.compile(
    r"\\begin\{(?P<kind>figure|table)\}.*?"
    r"\\caption\{(?P<caption>[^}]*)\}.*?"
    r"\\label\{(?P<label>[^}]*)\}(?P<body>.*?)"
    r"(?:\\fignotes\{(?P<note>.*?)\})?"
    r"\\end\{(?P=kind)\}",
    re.S,
)
LONGTABLE_PATTERN = re.compile(
    r"\\begin\{longtable\}(?P<body>.*?)"
    r"\\caption\{(?P<caption>[^}]*)\}\s*"
    r"\\label\{(?P<label>[^}]*)\}\\\\(?P<rest>.*?)"
    r"\\end\{longtable\}",
    re.S,
)


@dataclass
class DisplayBlock:
    kind: str
    order: int
    label: str
    caption: str
    note: str
    asset_name: str
    public_path: str


PREAMBLE = r"""
\documentclass[varwidth=185mm,border=8pt]{standalone}
\usepackage{amsmath,amssymb,graphicx,booktabs,array,longtable,multirow,makecell,float,xcolor}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,shapes.geometric,fit,calc,backgrounds,decorations.pathreplacing}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}
\newcolumntype{R}[1]{>{\raggedleft\arraybackslash}p{#1}}
\begin{document}
"""


def clean_text(text: str) -> str:
    text = text.replace("\n", " ").strip()
    replacements = {
        r"\&": "&",
        r"\%": "%",
        r"\_": "_",
        r"\#": "#",
        r"\$": "$",
        r"\rightarrow": "→",
        r"\textemdash": "—",
        r"\linebreak[2]": " ",
        r"\newline": " ",
        "~": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\\\((.*?)\\\)", lambda m: m.group(1), text)
    text = re.sub(r"\$(.*?)\$", lambda m: m.group(1), text)
    while True:
        updated = re.sub(r"\\(?:textbf|textit|emph|texttt|url|repoURL)\{([^{}]*)\}", r"\1", text)
        updated = re.sub(r"\\(?:citep|citet|citeyearpar|ref)\{([^{}]*)\}", r"\1", updated)
        if updated == text:
            break
        text = updated
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", "", text)
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def resolve_relative_path(raw_path: str, build_dir: Path) -> str:
    asset_path = (PAPER_DIR / raw_path).resolve()
    return Path(os.path.relpath(asset_path, build_dir)).as_posix()


def rewrite_block_paths(content: str, build_dir: Path) -> str:
    def replace_graphics(match: re.Match[str]) -> str:
        options = match.group(1) or ""
        raw_path = match.group(2)
        new_path = resolve_relative_path(raw_path, build_dir)
        return rf"\includegraphics{options}{{{new_path}}}"

    def replace_input(match: re.Match[str]) -> str:
        raw_path = match.group(1)
        new_path = resolve_relative_path(raw_path, build_dir)
        return rf"\input{{{new_path}}}"

    content = re.sub(r"\\includegraphics(\[[^\]]*\])?\{([^}]*)\}", replace_graphics, content)
    content = re.sub(r"\\input\{([^}]*)\}", replace_input, content)
    return content


def extract_render_body(kind: str, body: str) -> str:
    body = body.split(r"\fignotes{", 1)[0]
    if kind == "figure":
        match = re.search(r"\\centering(?P<content>.*)", body, re.S)
        return (match.group("content") if match else body).strip()
    match = re.search(r"\\centering(?P<content>.*)", body, re.S)
    return (match.group("content") if match else body).strip()


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def render_pdf_to_png(pdf_path: Path, out_base: Path) -> None:
    out_base.parent.mkdir(parents=True, exist_ok=True)
    run([PDFTOCAIRO, "-png", "-singlefile", "-r", "220", str(pdf_path), str(out_base)], cwd=pdf_path.parent)


def render_standalone(content: str, asset_base: str) -> Path:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    tex_path = BUILD_DIR / f"{asset_base}.tex"
    pdf_path = BUILD_DIR / f"{asset_base}.pdf"
    png_base = DISPLAY_PUBLIC_DIR / asset_base

    rewritten = rewrite_block_paths(content, BUILD_DIR)
    tex_source = PREAMBLE + "\n" + rewritten + "\n\\end{document}\n"
    tex_path.write_text(tex_source, encoding="utf-8")
    run([TECTONIC, str(tex_path)], cwd=BUILD_DIR)
    render_pdf_to_png(pdf_path, png_base)
    return png_base.with_suffix(".png")


def copy_or_convert_graphic(raw_path: str, asset_base: str) -> Path:
    source = (PAPER_DIR / raw_path).resolve()
    target = DISPLAY_PUBLIC_DIR / f"{asset_base}{source.suffix.lower()}"
    DISPLAY_PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".png":
        shutil.copy2(source, target)
        return target
    if source.suffix.lower() == ".pdf":
        png_base = DISPLAY_PUBLIC_DIR / asset_base
        render_pdf_to_png(source, png_base)
        return png_base.with_suffix(".png")
    raise ValueError(f"Unsupported graphic type: {source}")


def parse_blocks() -> list[DisplayBlock]:
    tex = TEX_SOURCE.read_text(encoding="utf-8")
    figure_order = 0
    table_order = 0
    blocks: list[DisplayBlock] = []
    parsed: list[tuple[int, str, str, str, str, str]] = []

    for match in ENV_PATTERN.finditer(tex):
        parsed.append(
            (
                match.start(),
                match.group("kind"),
                match.group("label"),
                clean_text(match.group("caption")),
                clean_text(match.group("note") or ""),
                extract_render_body(match.group("kind"), match.group("body")),
            )
        )

    for match in LONGTABLE_PATTERN.finditer(tex):
        block = "\\begin{longtable}" + match.group("body") + "\\caption{" + match.group("caption") + "}\\label{" + match.group("label") + "}\\\\" + match.group("rest") + "\\end{longtable}"
        parsed.append(
            (
                match.start(),
                "table",
                match.group("label"),
                clean_text(match.group("caption")),
                "",
                block.strip(),
            )
        )

    parsed.sort(key=lambda item: item[0])

    for _, kind, label, caption, note, body in parsed:

        if kind == "figure":
            figure_order += 1
            asset_base = f"figure-{figure_order:02d}-{label.replace(':', '-')}"
            graphic_match = re.search(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}", body)
            if graphic_match and "\\begin{tikzpicture}" not in body:
                rendered = copy_or_convert_graphic(graphic_match.group(1), asset_base)
            else:
                rendered = render_standalone(body, asset_base)
            order = figure_order
        else:
            table_order += 1
            asset_base = f"table-{table_order:02d}-{label.replace(':', '-')}"
            rendered = render_standalone(body, asset_base)
            order = table_order

        public_path = "/" + rendered.relative_to(SITE_PUBLIC).as_posix()
        blocks.append(
            DisplayBlock(
                kind=kind,
                order=order,
                label=label,
                caption=caption,
                note=note,
                asset_name=rendered.name,
                public_path=public_path,
            )
        )

    return blocks


def write_manifest(blocks: list[DisplayBlock]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "figures": [
            {
                "number": block.order,
                "label": block.label,
                "caption": block.caption,
                "note": block.note,
                "public_path": block.public_path,
            }
            for block in blocks
            if block.kind == "figure"
        ],
        "tables": [
            {
                "number": block.order,
                "label": block.label,
                "caption": block.caption,
                "note": block.note,
                "public_path": block.public_path,
            }
            for block in blocks
            if block.kind == "table"
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    blocks = parse_blocks()
    write_manifest(blocks)
    print(f"Rendered {sum(1 for b in blocks if b.kind == 'figure')} figures and {sum(1 for b in blocks if b.kind == 'table')} tables.")


if __name__ == "__main__":
    main()
