#!/usr/bin/env python3
"""Move every local image referenced as ![alt](path) in the repo's markdown
files into <repo>/imgs/, renaming it to the next free number (001.png, ...),
and rewrite the markdown links to point at the new location.

Usage: reorganize_images.py [--dry-run]
"""
import os
import re
import shutil
import subprocess
import sys
from urllib.parse import quote, unquote

IMG_RE = re.compile(r'(!\[[^\]]*\]\()\s*(<[^>]+>|[^)\s]+)(\s+"[^"]*")?\s*(\))')
NUM_RE = re.compile(r'^(\d+)\.[^.]+$')

dry = "--dry-run" in sys.argv
root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
imgs_dir = os.path.join(root, "imgs")

# Markdown files known to git (tracked or untracked, respecting .gitignore).
md_files = subprocess.check_output(
    ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"],
    cwd=root, text=True).split()
md_files = [os.path.join(root, f) for f in md_files if not f.startswith(".claude/")]

existing = [int(m.group(1)) for f in (os.listdir(imgs_dir) if os.path.isdir(imgs_dir) else [])
            if (m := NUM_RE.match(f))]
next_num = max(existing, default=0) + 1
moved = {}  # old abs path -> new abs path


def relocate(md_path, target):
    global next_num
    raw = target[1:-1] if target.startswith("<") else target
    if re.match(r'^[a-z][a-z0-9+.-]*:', raw, re.I) or raw.startswith("#"):
        return None  # remote URL / data URI / anchor
    src = os.path.normpath(os.path.join(os.path.dirname(md_path), unquote(raw)))
    if src in moved:
        new = moved[src]
    else:
        if os.path.dirname(src) == imgs_dir and NUM_RE.match(os.path.basename(src)):
            return None  # already reorganized
        if not os.path.isfile(src):
            print(f"  ! missing: {raw} (in {os.path.relpath(md_path, root)})")
            return None
        ext = os.path.splitext(src)[1].lower()
        new = os.path.join(imgs_dir, f"{next_num:03d}{ext}")
        next_num += 1
        moved[src] = new
        print(f"  {os.path.relpath(src, root)} -> {os.path.relpath(new, root)}")
        if not dry:
            os.makedirs(imgs_dir, exist_ok=True)
            shutil.move(src, new)
    return quote(os.path.relpath(new, os.path.dirname(md_path)))


for md in md_files:
    with open(md, encoding="utf-8") as fh:
        text = fh.read()

    def sub(m):
        new = relocate(md, m.group(2))
        if new is None:
            return m.group(0)
        return f"{m.group(1)}{new}{m.group(3) or ''}{m.group(4)}"

    updated = IMG_RE.sub(sub, text)
    if updated != text:
        print(f"updated {os.path.relpath(md, root)}")
        if not dry:
            with open(md, "w", encoding="utf-8") as fh:
                fh.write(updated)

print(f"{len(moved)} image(s) {'would be ' if dry else ''}moved")
