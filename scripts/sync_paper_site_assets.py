from __future__ import annotations

import re
import shutil
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = ROOT / "site"
PUBLIC_ASSETS_DIR = SITE_ROOT / "public" / "paper-assets"
GENERATED_PAPER_DIR = SITE_ROOT / "src" / "generated" / "paper"
MANIFEST_TARGET = GENERATED_PAPER_DIR / "paper_manifest.json"
DISPLAY_MANIFEST_TARGET = GENERATED_PAPER_DIR / "paper_display_manifest.json"
WORKING_PAPER_PDF_SOURCE = ROOT / "paper" / "research_allocation_paper.pdf"
WORKING_PAPER_PDF_TARGET = SITE_ROOT / "public" / "downloads" / "frontiergraph-working-paper.pdf"
DISPLAY_RENDER_SCRIPT = ROOT / "scripts" / "render_paper_display_assets.py"

FULL_SOURCE = ROOT / "paper" / "research_allocation_paper.md"
OVERVIEW_SOURCE = ROOT / "paper" / "research_allocation_paper_web.md"
FULL_TARGET = GENERATED_PAPER_DIR / "research_allocation_paper_full.md"
OVERVIEW_TARGET = GENERATED_PAPER_DIR / "research_allocation_paper_overview.md"

IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
HEADING_PATTERN = re.compile(r"^(##|###)\s+(.+)$", re.MULTILINE)
NOTES_PARAGRAPH_PATTERN = re.compile(r"(?:^|\n)\*\*Notes\.\*\*.*?(?=\n## |\n### |\n#### |\Z)", re.S)

MAIN_FIGURE_INSERTIONS = {
    "### 3.2 Paper-local research graphs": ["fig:extraction-flow"],
    "### 3.3 Concept identity and node normalization": [
        "fig:shared-candidate-formation",
        "fig:real-neighborhood",
    ],
    "### 4.1 Missing links as retrieval anchors": ["fig:candidate-schematic"],
    "### 4.2 Gap and boundary questions": ["fig:gap-boundary"],
    "### 4.3 How the score reads the graph": ["fig:score-components"],
    "### 4.4 Prospective evaluation": ["fig:evaluation-design"],
    "### 5.1 Popularity at the strict shortlist": ["fig:main-benchmark"],
    "### 5.5 Path development and the richer surfaced object": [
        "fig:path-evolution",
        "fig:path-source-mix",
    ],
    "## Appendix B. Node normalization and ontology construction": ["fig:normalization-flow"],
}

MAIN_TABLE_INSERTIONS = {
    "### 5.1 Popularity at the strict shortlist": ["tab:benchmark-summary-main"],
}


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return cleaned or "section"


def strip_title_block(markdown: str) -> str:
    lines = markdown.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == "## Abstract":
            return "\n".join(lines[index:]).strip() + "\n"
    return markdown


def run_render_sync() -> None:
    subprocess.run(["python3", str(DISPLAY_RENDER_SCRIPT)], check=True, cwd=ROOT)


def sync_working_paper_pdf() -> None:
    ensure_dir(WORKING_PAPER_PDF_TARGET)
    shutil.copy2(WORKING_PAPER_PDF_SOURCE, WORKING_PAPER_PDF_TARGET)


def rewrite_images(markdown: str, source_path: Path) -> str:
    def replace(match: re.Match[str]) -> str:
        alt_text, raw_path = match.groups()
        raw_path = raw_path.strip()
        if raw_path.startswith(("http://", "https://", "/")):
            return match.group(0)

        asset_path = (source_path.parent / raw_path).resolve()
        if not asset_path.exists():
            return match.group(0)

        try:
            relative_asset = asset_path.relative_to(ROOT)
        except ValueError:
            relative_asset = Path(asset_path.name)
        target_path = PUBLIC_ASSETS_DIR / relative_asset
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset_path, target_path)
        public_path = "/" + target_path.relative_to(SITE_ROOT / "public").as_posix()
        return f"![{alt_text}]({public_path})"

    return IMAGE_PATTERN.sub(replace, markdown)


def strip_markdown_tables(markdown: str) -> str:
    cleaned_lines: list[str] = []
    lines = markdown.splitlines()
    in_table = False
    keep_schema_tables = False
    for line in lines:
        if line.strip() == "### Schema":
            keep_schema_tables = True
        elif keep_schema_tables and line.startswith("### ") and line.strip() != "### Schema":
            keep_schema_tables = False
        if keep_schema_tables:
            cleaned_lines.append(line)
            continue
        if line.lstrip().startswith("|"):
            in_table = True
            continue
        if in_table and not line.strip():
            in_table = False
            continue
        if in_table:
            in_table = False
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def strip_markdown_images(markdown: str) -> str:
    return IMAGE_PATTERN.sub("", markdown)


def strip_notes_paragraphs(markdown: str) -> str:
    return NOTES_PARAGRAPH_PATTERN.sub("\n", markdown)


def load_display_manifest() -> dict[str, list[dict[str, str | int]]]:
    return json.loads(DISPLAY_MANIFEST_TARGET.read_text(encoding="utf-8"))


def block_html(item: dict[str, str | int], kind_label: str) -> str:
    note_html = ""
    if item.get("note"):
        note_html = f'\n  <p class="paper-display-note">{item["note"]}</p>'
    return (
        f'<figure class="paper-display-block {"paper-display-table" if kind_label == "Table" else ""}" '
        f'id="{item["label"]}">\n'
        f'  <img src="{item["public_path"]}" alt="{item["caption"]}" loading="lazy" />\n'
        f'  <figcaption><strong>{kind_label} {item["number"]}.</strong> {item["caption"]}</figcaption>'
        f"{note_html}\n"
        f"</figure>"
    )


def insert_after_heading(markdown: str, heading: str, blocks: list[str]) -> str:
    marker = heading + "\n"
    if marker not in markdown:
        return markdown
    insertion = marker + "\n".join(blocks) + "\n"
    return markdown.replace(marker, insertion, 1)


def inject_display_blocks(markdown: str, manifest: dict[str, list[dict[str, str | int]]]) -> str:
    figures = {item["label"]: item for item in manifest["figures"]}
    tables = {item["label"]: item for item in manifest["tables"]}
    inserted_figure_labels: set[str] = set()
    inserted_table_labels: set[str] = set()

    for heading, labels in MAIN_FIGURE_INSERTIONS.items():
        blocks = []
        for label in labels:
            item = figures.get(label)
            if item:
                blocks.append(block_html(item, "Figure"))
                inserted_figure_labels.add(label)
        if blocks:
            markdown = insert_after_heading(markdown, heading, blocks)

    for heading, labels in MAIN_TABLE_INSERTIONS.items():
        blocks = []
        for label in labels:
            item = tables.get(label)
            if item:
                blocks.append(block_html(item, "Table"))
                inserted_table_labels.add(label)
        if blocks:
            markdown = insert_after_heading(markdown, heading, blocks)

    remaining_figures = [item for item in manifest["figures"] if item["label"] not in inserted_figure_labels]
    remaining_tables = [item for item in manifest["tables"] if item["label"] not in inserted_table_labels]

    appendix_parts: list[str] = [
        "## Display appendix",
        "",
        "The blocks below are rendered directly from the current paper source so the HTML page carries the same figure and table inventory as the PDF, including the appendix items.",
        "",
    ]
    if remaining_figures:
        appendix_parts.extend(["### Remaining figures", ""])
        appendix_parts.extend(block_html(item, "Figure") for item in remaining_figures)
        appendix_parts.append("")
    if remaining_tables:
        appendix_parts.extend(["### Tables", ""])
        appendix_parts.extend(block_html(item, "Table") for item in remaining_tables)
        appendix_parts.append("")

    appendix_block = "\n".join(appendix_parts)
    references_heading = "\n## References"
    if references_heading in markdown:
        markdown = markdown.replace(references_heading, "\n" + appendix_block + "\n## References", 1)
    else:
        markdown = markdown.rstrip() + "\n\n" + appendix_block + "\n"
    return markdown


def add_frontmatter(markdown: str, *, title: str, description: str, eyebrow: str, author: str, date: str) -> str:
    frontmatter = (
        "---\n"
        f'title: "{title}"\n'
        f'description: "{description}"\n'
        f'eyebrow: "{eyebrow}"\n'
        f'author: "{author}"\n'
        f'date: "{date}"\n'
        "---\n\n"
    )
    return frontmatter + markdown.lstrip()


def heading_id(text: str) -> str:
    cleaned = re.sub(r"[`*]", "", text).strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned).strip("-")
    return cleaned or "section"


def extract_headings(markdown: str) -> list[dict[str, str | int]]:
    headings: list[dict[str, str | int]] = []
    for match in HEADING_PATTERN.finditer(markdown):
        level, raw_text = match.groups()
        text = raw_text.strip()
        headings.append(
            {
                "level": 2 if level == "##" else 3,
                "text": text,
                "id": heading_id(text),
            }
        )
    return headings


def transform_full_markdown() -> str:
    markdown = FULL_SOURCE.read_text(encoding="utf-8")
    markdown = strip_title_block(markdown)
    markdown = strip_markdown_images(markdown)
    markdown = strip_notes_paragraphs(markdown)
    markdown = strip_markdown_tables(markdown)
    markdown = rewrite_images(markdown, FULL_SOURCE)
    markdown = inject_display_blocks(markdown, load_display_manifest())
    return add_frontmatter(
        markdown,
        title="What Should Economics Ask Next?",
        description="Full HTML manuscript for the current Frontier Graph paper.",
        eyebrow="Paper",
        author="Prashant Garg",
        date="12 April 2026",
    )


def transform_overview_markdown() -> str:
    markdown = OVERVIEW_SOURCE.read_text(encoding="utf-8")
    markdown = rewrite_images(markdown, OVERVIEW_SOURCE)
    return add_frontmatter(
        markdown,
        title="What Frontier Graph Finds",
        description="A web-first overview of the Frontier Graph paper and public release.",
        eyebrow="Web overview",
        author="Prashant Garg",
        date="12 April 2026",
    )


def main() -> None:
    run_render_sync()
    sync_working_paper_pdf()
    GENERATED_PAPER_DIR.mkdir(parents=True, exist_ok=True)
    ensure_dir(FULL_TARGET)
    ensure_dir(OVERVIEW_TARGET)
    full_markdown = transform_full_markdown()
    overview_markdown = transform_overview_markdown()
    FULL_TARGET.write_text(full_markdown, encoding="utf-8")
    OVERVIEW_TARGET.write_text(overview_markdown, encoding="utf-8")
    MANIFEST_TARGET.write_text(
        json.dumps(
            {
                "full": {
                    "title": "What Should Economics Ask Next?",
                    "eyebrow": "Paper",
                    "headings": extract_headings(full_markdown),
                },
                "overview": {
                    "title": "What Frontier Graph Finds",
                    "eyebrow": "Web overview",
                    "headings": extract_headings(overview_markdown),
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print("Synced paper markdown and figure assets for the website.")


if __name__ == "__main__":
    main()
