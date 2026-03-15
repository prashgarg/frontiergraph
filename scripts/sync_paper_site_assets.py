from __future__ import annotations

import re
import shutil
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = ROOT / "site"
PUBLIC_ASSETS_DIR = SITE_ROOT / "public" / "paper-assets"
GENERATED_PAPER_DIR = SITE_ROOT / "src" / "generated" / "paper"
MANIFEST_TARGET = GENERATED_PAPER_DIR / "paper_manifest.json"

FULL_SOURCE = ROOT / "paper" / "research_allocation_paper.md"
OVERVIEW_SOURCE = ROOT / "paper" / "research_allocation_paper_web.md"
FULL_TARGET = GENERATED_PAPER_DIR / "research_allocation_paper_full.md"
OVERVIEW_TARGET = GENERATED_PAPER_DIR / "research_allocation_paper_overview.md"

IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
HEADING_PATTERN = re.compile(r"^(##|###)\s+(.+)$", re.MULTILINE)


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
    markdown = rewrite_images(markdown, FULL_SOURCE)
    return add_frontmatter(
        markdown,
        title="What Should Economics Work On Next?",
        description="Full HTML manuscript for the FrontierGraph working paper.",
        eyebrow="Working paper",
        author="Prashant Garg",
        date="15 March 2026",
    )


def transform_overview_markdown() -> str:
    markdown = OVERVIEW_SOURCE.read_text(encoding="utf-8")
    markdown = rewrite_images(markdown, OVERVIEW_SOURCE)
    return add_frontmatter(
        markdown,
        title="What FrontierGraph Finds",
        description="A web-first overview of the FrontierGraph paper and public release.",
        eyebrow="Web overview",
        author="Prashant Garg",
        date="15 March 2026",
    )


def main() -> None:
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
                    "title": "What Should Economics Work On Next?",
                    "eyebrow": "Working paper",
                    "headings": extract_headings(full_markdown),
                },
                "overview": {
                    "title": "What FrontierGraph Finds",
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
