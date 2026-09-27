#!/usr/bin/env python3
"""Move every local image referenced as ![alt](path) in the repo's markdown
files into <repo>/imgs/, renaming it to the next free number (001.png, ...),
and rewrite the markdown links to point at the new location. Image files that
no markdown file references afterwards are moved to <repo>/tmp/.

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
HTML_IMG_RE = re.compile(r'<img\b[^>]*\bsrc\s*=\s*["\']([^"\']+)["\']', re.I)
IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".tif", ".tiff", ".avif", ".heic"}
SKIP_DIRS = (".claude/", "tmp/")

dry = "--dry-run" in sys.argv
root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
imgs_dir = os.path.join(root, "imgs")
tmp_dir = os.path.join(root, "tmp")


def git_files(pattern):
    """Files known to git (tracked or untracked, respecting .gitignore)."""
    out = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", pattern],
        cwd=root, text=True).splitlines()
    return [os.path.join(root, f) for f in out if not f.startswith(SKIP_DIRS)]


md_files = git_files("*.md")

existing = [int(m.group(1)) for f in (os.listdir(imgs_dir) if os.path.isdir(imgs_dir) else [])
            if (m := NUM_RE.match(f))]
next_num = max(existing, default=0) + 1
moved = {}  # old abs path -> new abs path
used = set()  # abs paths of images referenced by some markdown file


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
            used.add(src)
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
    used.add(new)
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
    # <img src="..."> tags are left in place but count as uses.
    for src in HTML_IMG_RE.findall(updated):
        used.add(os.path.normpath(os.path.join(os.path.dirname(md), unquote(src))))
    if updated != text:
        print(f"updated {os.path.relpath(md, root)}")
        if not dry:
            with open(md, "w", encoding="utf-8") as fh:
                fh.write(updated)

print(f"{len(moved)} image(s) {'would be ' if dry else ''}moved to imgs/")

# Park image files that nothing references in tmp/.
unused = [f for f in git_files("*")
          if os.path.splitext(f)[1].lower() in IMG_EXTS and f not in used and f not in moved]
for src in sorted(unused):
    base, ext = os.path.splitext(os.path.basename(src))
    dest, n = os.path.join(tmp_dir, base + ext), 1
    while os.path.exists(dest):
        dest, n = os.path.join(tmp_dir, f"{base}-{n}{ext}"), n + 1
    print(f"  unused: {os.path.relpath(src, root)} -> {os.path.relpath(dest, root)}")
    if not dry:
        os.makedirs(tmp_dir, exist_ok=True)
        shutil.move(src, dest)
print(f"{len(unused)} unused image(s) {'would be ' if dry else ''}moved to tmp/")
