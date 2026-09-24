#!/usr/bin/env python3
"""
Render mermaid diagrams to PNG using Playwright + mermaid.js CDN.
"""
import asyncio
import os
import re
import base64
from pathlib import Path
from playwright.async_api import async_playwright

DOCS_DIR = Path("/app/docs")
IMAGES_DIR = DOCS_DIR / "images"
IMAGES_DIR.mkdir(exist_ok=True)

FILES_WITH_DIAGRAMS = [
    "03-system-design/diagrams/architecture.md",
    "03-system-design/diagrams/erd.md",
    "03-system-design/diagrams/sequences.md",
]

HTML_TEMPLATE = """<!DOCTYPE html>
<html><head>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<style>
body {{ margin: 0; padding: 40px; background: white; }}
#diagram {{ display: inline-block; }}
.mermaid svg {{ min-width: 800px; }}
</style>
</head><body>
<div id="diagram" class="mermaid">
{code}
</div>
<script>
mermaid.initialize({{
    startOnLoad: true,
    theme: 'default',
    securityLevel: 'loose',
    fontSize: 16,
    flowchart: {{ curve: 'basis', padding: 20 }},
    sequence: {{ actorMargin: 80, messageFontSize: 15, noteFontSize: 14, actorFontSize: 15 }},
    er: {{ fontSize: 16 }}
}});
</script>
</body></html>"""


def extract_mermaid_blocks(md_content):
    pattern = r'```mermaid\n(.*?)```'
    blocks = []
    for match in re.finditer(pattern, md_content, re.DOTALL):
        blocks.append({
            'start': match.start(),
            'end': match.end(),
            'code': match.group(1).strip()
        })
    return blocks


async def render_diagram(page, mermaid_code, output_path, timeout=15000):
    """Render a single mermaid diagram."""
    html = HTML_TEMPLATE.format(code=mermaid_code)
    temp_html = "/tmp/mermaid_render.html"
    with open(temp_html, 'w') as f:
        f.write(html)

    await page.goto(f"file://{temp_html}")
    await page.wait_for_timeout(2000)

    # Wait for mermaid to render
    try:
        await page.wait_for_selector("svg", timeout=timeout)
        await page.wait_for_timeout(500)
    except Exception:
        print("TIMEOUT waiting for SVG")
        return False

    # Get the diagram element bounds
    diagram = await page.query_selector("#diagram")
    if not diagram:
        diagram = await page.query_selector("svg")
    if not diagram:
        return False

    bbox = await diagram.bounding_box()
    if not bbox or bbox['width'] < 10 or bbox['height'] < 10:
        return False

    # Screenshot just the diagram
    await diagram.screenshot(path=str(output_path), type="png")
    return output_path.exists() and output_path.stat().st_size > 100


async def process_file(page, rel_path):
    md_file = DOCS_DIR / rel_path
    if not md_file.exists():
        print(f"  SKIP: {rel_path}")
        return

    content = md_file.read_text(encoding='utf-8')
    blocks = extract_mermaid_blocks(content)

    # Self-heal: if the live file has no mermaid blocks but a saved source
    # exists, restore from the source. This makes re-runs idempotent —
    # otherwise re-running the renderer is a no-op once the .md has been
    # collapsed to image references.
    src_path = (DOCS_DIR / rel_path).parent / "_sources" / Path(rel_path).name
    if not blocks and src_path.exists():
        print(f"  RESTORE: {rel_path} from _sources/")
        content = src_path.read_text(encoding='utf-8')
        md_file.write_text(content, encoding='utf-8')
        blocks = extract_mermaid_blocks(content)

    if not blocks:
        print(f"  SKIP: {rel_path} (no mermaid blocks)")
        return

    print(f"  {rel_path}: {len(blocks)} diagram(s)")
    base_name = Path(rel_path).stem

    # Preserve the mermaid source — the rest of this function REPLACES the
    # source with image references in-place, so without this backup the
    # next render run has nothing to regenerate from.
    src_dir = (DOCS_DIR / rel_path).parent / "_sources"
    src_dir.mkdir(exist_ok=True)
    (src_dir / Path(rel_path).name).write_text(content, encoding='utf-8')

    new_content = content
    for i, block in enumerate(reversed(blocks)):
        idx = len(blocks) - 1 - i
        img_filename = f"{base_name}_{idx + 1}.png"
        img_path = IMAGES_DIR / img_filename

        print(f"    [{idx+1}/{len(blocks)}] Rendering...", end=" ", flush=True)
        success = await render_diagram(page, block['code'], img_path)

        if success:
            size_kb = img_path.stat().st_size // 1024
            print(f"OK ({size_kb}KB)")

            md_dir = (DOCS_DIR / rel_path).parent
            rel_img_path = os.path.relpath(img_path, md_dir)

            # Get title from preceding heading
            preceding = new_content[:block['start']]
            title_match = re.findall(r'(?:^|\n)#+\s+(.+)', preceding)
            alt_text = title_match[-1].strip() if title_match else f"Diagram {idx + 1}"

            replacement = f"![{alt_text}]({rel_img_path})"
            new_content = new_content[:block['start']] + replacement + new_content[block['end']:]
        else:
            print("FAILED")

    md_file.write_text(new_content, encoding='utf-8')
    print(f"  Saved: {rel_path}")


async def main():
    print("=" * 60)
    print("Mermaid Diagram Renderer (Playwright)")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            viewport={"width": 1800, "height": 1200},
            device_scale_factor=3
        )

        for rel_path in FILES_WITH_DIAGRAMS:
            await process_file(page, rel_path)

        await browser.close()

    images = sorted(IMAGES_DIR.glob("*.png"))
    print(f"\nGenerated {len(images)} images:")
    for img in images:
        print(f"  {img.name} ({img.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    asyncio.run(main())
