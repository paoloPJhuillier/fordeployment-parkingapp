#!/usr/bin/env python3
"""
Extract mermaid code blocks from markdown files, render to PNG,
and replace the code blocks with image references.
"""
import os
import re
import json
import subprocess
import base64
from pathlib import Path

DOCS_DIR = Path("/app/docs")
IMAGES_DIR = DOCS_DIR / "images"
IMAGES_DIR.mkdir(exist_ok=True)

FILES_WITH_DIAGRAMS = [
    "03-system-design/diagrams/architecture.md",
    "03-system-design/diagrams/erd.md",
    "03-system-design/diagrams/sequences.md",
]

def extract_mermaid_blocks(md_content):
    """Extract all mermaid code blocks with positions."""
    pattern = r'```mermaid\n(.*?)```'
    blocks = []
    for match in re.finditer(pattern, md_content, re.DOTALL):
        blocks.append({
            'start': match.start(),
            'end': match.end(),
            'code': match.group(1).strip()
        })
    return blocks


def render_mermaid_to_png(mermaid_code, output_path, index):
    """Render a mermaid diagram to PNG using mmdc CLI."""
    # Write mermaid code to temp file
    temp_mmd = f"/tmp/diagram_{index}.mmd"
    with open(temp_mmd, 'w') as f:
        f.write(mermaid_code)
    
    # Render with mmdc
    cmd = [
        "npx", "@mermaid-js/mermaid-cli",
        "-i", temp_mmd,
        "-o", str(output_path),
        "-b", "white",
        "-w", "1200",
        "--scale", "2"
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        cwd="/app/frontend"
    )
    
    if result.returncode != 0:
        print(f"  WARN: mmdc failed for diagram {index}: {result.stderr[:200]}")
        return False
    
    if output_path.exists() and output_path.stat().st_size > 0:
        return True
    return False


def process_file(rel_path):
    """Process a markdown file: extract mermaid, render, replace."""
    md_file = DOCS_DIR / rel_path
    if not md_file.exists():
        print(f"  SKIP: {rel_path} not found")
        return
    
    content = md_file.read_text(encoding='utf-8')
    blocks = extract_mermaid_blocks(content)
    
    if not blocks:
        print(f"  SKIP: {rel_path} has no mermaid blocks")
        return
    
    print(f"  Processing {rel_path}: {len(blocks)} diagram(s)")
    
    # Determine base name for images
    base_name = Path(rel_path).stem
    
    # Process in reverse order so positions don't shift
    new_content = content
    for i, block in enumerate(reversed(blocks)):
        idx = len(blocks) - 1 - i
        img_filename = f"{base_name}_{idx + 1}.png"
        img_path = IMAGES_DIR / img_filename
        
        print(f"    Rendering diagram {idx + 1}...", end=" ")
        success = render_mermaid_to_png(block['code'], img_path, f"{base_name}_{idx}")
        
        if success:
            size_kb = img_path.stat().st_size // 1024
            print(f"OK ({size_kb}KB)")
            # Relative path from the markdown file to the images dir
            md_dir = (DOCS_DIR / rel_path).parent
            rel_img_path = os.path.relpath(img_path, md_dir)
            
            # Find a title for the diagram from the preceding heading or text
            # Look back from block start for a heading
            preceding = new_content[:block['start']]
            title_match = re.findall(r'(?:^|\n)#+\s+(.+)', preceding)
            alt_text = title_match[-1].strip() if title_match else f"Diagram {idx + 1}"
            
            # Replace mermaid block with image
            replacement = f"![{alt_text}]({rel_img_path})"
            new_content = new_content[:block['start']] + replacement + new_content[block['end']:]
        else:
            print("FAILED (keeping text)")
    
    # Write updated markdown
    md_file.write_text(new_content, encoding='utf-8')
    print(f"  Updated: {rel_path}")


def main():
    print("=" * 60)
    print("Mermaid Diagram Renderer")
    print("=" * 60)
    
    for rel_path in FILES_WITH_DIAGRAMS:
        process_file(rel_path)
    
    # Count generated images
    images = list(IMAGES_DIR.glob("*.png"))
    print(f"\nGenerated {len(images)} diagram images in {IMAGES_DIR}")
    for img in sorted(images):
        print(f"  {img.name} ({img.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    main()
