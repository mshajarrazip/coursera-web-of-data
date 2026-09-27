---
name: reorganize
description: Tidy up the notes repo. Use when the user says "reorganize". Moves every local markdown image (![alt](path)) into ./imgs with a numbered filename and rewrites the links, and moves image files no markdown references into ./tmp.
---

# Reorganize

Run each step below in order, then report what changed.

## 1. Collect markdown images into `imgs/`

Every local image referenced with `![alt](path)` in the repo's `.md` files is moved to `<repo root>/imgs/` and renamed to the next free number (`001.png`, `002.jpg`, ... keeping the original extension). The link in the source markdown is rewritten to the new relative path (e.g. `notes/x.md` gets `../imgs/001.png`).

Run the script (from anywhere inside the repo):

```sh
python3 .claude/skills/reorganize/reorganize_images.py --dry-run   # preview
python3 .claude/skills/reorganize/reorganize_images.py             # apply
```

Behavior:
- Numbering continues after the highest existing number in `imgs/`.
- Images already at `imgs/NNN.ext` are left alone, so re-running is safe.
- Remote URLs (`http://...`), data URIs and anchors are skipped.
- An image referenced from several places is moved once and every link is updated.
- Missing image files are reported and their links left untouched.
- Only markdown files git sees are scanned (gitignored paths are skipped, and so are `tmp/` and `.claude/`).

## 2. Park unused images in `tmp/`

The same script run also handles unused images. After step 1, any image file in the repo (outside `tmp/` and `.claude/`) that no markdown file references is moved to `<repo root>/tmp/`, keeping its name. If that name is already taken, it adds `-1`, `-2`, and so on. This includes `imgs/NNN` files whose links were deleted, which leaves gaps in the numbering. Images used through an HTML `<img src="...">` tag in markdown count as used and stay where they are.

After running, show the user the list of moves (to `imgs/` and to `tmp/`) and mention any missing images.
