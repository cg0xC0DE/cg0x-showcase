#!/usr/bin/env python3
"""
cover-design-organize.py — cg0x-cover-design 图片整理脚本

扁平结构：所有图片存放在 gallery/{fid}.png，catalog.json 记录元数据。
incoming/ 中的新图片自动分配 fid 并移入 gallery/。

目录结构：
  cg0x-cover-design/
    catalog.json       ← 全局索引
    gallery/           ← 所有图片（{fid}.png）
    incoming/          ← 待整理的新图片

用法：
  python tools/cover-design-organize.py                 # 处理 incoming + 检查
  python tools/cover-design-organize.py --dry-run       # 预览，不移动文件
  python tools/cover-design-organize.py --check         # 仅检查完整性
  python tools/cover-design-organize.py --migrate-old   # 一次性：旧 gid 目录 → gallery/
"""

import json
import random
import shutil
import string
import sys
from datetime import datetime
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
REPO_DIR = SCRIPT_DIR.parent
PROJECT = "cg0x-cover-design"
PROJ_DIR = REPO_DIR / PROJECT
GALLERY_DIR = PROJ_DIR / "gallery"
INCOMING_DIR = PROJ_DIR / "incoming"
CATALOG_PATH = PROJ_DIR / "catalog.json"

IMAGE_EXT = ".png"
CURRENT_BATCH = datetime.now().strftime("%Y-%m")


# ── Helpers ───────────────────────────────────────────────────────────────

def gen_id(used: set, k: int = 4) -> str:
    chars = string.ascii_lowercase + string.digits
    while True:
        uid = "".join(random.choices(chars, k=k))
        if uid not in used:
            used.add(uid)
            return uid


def load_catalog() -> dict:
    if CATALOG_PATH.exists():
        return json.loads(CATALOG_PATH.read_text("utf-8"))
    return {"items": []}


def save_catalog(catalog: dict):
    CATALOG_PATH.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", "utf-8"
    )


def all_fids(catalog: dict) -> set:
    return {item["fid"] for item in catalog["items"]}


def scan_gallery() -> set:
    """Return set of fids from actual PNG files in gallery/."""
    if not GALLERY_DIR.exists():
        return set()
    return {f.stem for f in GALLERY_DIR.iterdir()
            if f.suffix == IMAGE_EXT and f.is_file()}


# ── Commands ──────────────────────────────────────────────────────────────

def cmd_sync(dry_run: bool):
    """Sync catalog with filesystem: add from incoming, remove deleted from gallery."""
    catalog = load_catalog()
    used = all_fids(catalog)
    changed = False

    # ── 1. Process incoming ──────────────────────────────────────────────
    added = 0
    if INCOMING_DIR.exists():
        files = sorted(f for f in INCOMING_DIR.iterdir()
                       if f.suffix == IMAGE_EXT and f.is_file())
        if files:
            existing_names = {item["name"] for item in catalog["items"]}
            print(f"Found {len(files)} images in incoming/")
            for f in files:
                name = f.stem
                if name in existing_names:
                    print(f"  SKIP (exists): {name}")
                    continue

                fid = gen_id(used)
                dst = GALLERY_DIR / f"{fid}{IMAGE_EXT}"

                if not dry_run:
                    GALLERY_DIR.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(f), str(dst))
                verb = "[dry]" if dry_run else "MOVE"
                print(f"  {verb} [{fid}] {name}")

                catalog["items"].append({
                    "fid": fid,
                    "name": name,
                    "batch": CURRENT_BATCH,
                })
                existing_names.add(name)
                added += 1
        else:
            print("incoming/ — no new images.")
    else:
        print("incoming/ — not found, skipping.")

    # ── 2. Detect deletions from gallery ─────────────────────────────────
    on_disk = scan_gallery()
    removed = 0
    kept = []
    for item in catalog["items"]:
        if item["fid"] not in on_disk:
            verb = "[dry]" if dry_run else "REMOVE"
            print(f"  {verb} from catalog: {item['fid']} ({item['name']})")
            removed += 1
        else:
            kept.append(item)

    if removed > 0:
        catalog["items"] = kept

    # ── 3. Summary & save ────────────────────────────────────────────────
    if added or removed:
        changed = True
        print(f"\n+{added} added, -{removed} removed.")
    else:
        print("\nNo changes.")

    if changed and not dry_run:
        save_catalog(catalog)
        print("catalog.json updated.")


def cmd_check():
    """Cross-check catalog against actual files in gallery/."""
    catalog = load_catalog()
    on_disk = scan_gallery()
    catalog_fids = all_fids(catalog)
    issues = []

    # On disk but not in catalog
    for fid in sorted(on_disk - catalog_fids):
        issues.append(f"  UNREGISTERED  gallery/{fid}.png")

    # In catalog but not on disk
    for item in catalog["items"]:
        if item["fid"] not in on_disk:
            issues.append(f"  MISSING       gallery/{item['fid']}.png  ({item['name']})")

    if issues:
        print(f"Issues ({len(issues)}):")
        for i in issues:
            print(i)
    else:
        print("Integrity: OK")

    print(f"Catalog: {len(catalog['items'])} entries | On disk: {len(on_disk)} images")


def cmd_migrate_old(dry_run: bool):
    """One-time migration: old {gid}/{fid}.png structure → flat gallery/{fid}.png.

    Reads old catalog.json (groups format), moves images, writes new catalog (items format).
    """
    old_catalog = load_catalog()

    # Detect format: old has "groups", new has "items"
    if "items" in old_catalog and "groups" not in old_catalog:
        print("Catalog is already in new format. Nothing to migrate.")
        return

    if "groups" not in old_catalog or not old_catalog["groups"]:
        print("No old-format catalog found.")
        return

    GALLERY_DIR.mkdir(parents=True, exist_ok=True)
    new_items = []
    moved = 0
    missing = 0

    for group in old_catalog["groups"]:
        gid = group["gid"]
        label = group.get("label", "")
        for item in group["items"]:
            fid = item["fid"]
            name = item.get("displayname", fid)
            src = PROJ_DIR / gid / f"{fid}{IMAGE_EXT}"
            dst = GALLERY_DIR / f"{fid}{IMAGE_EXT}"

            if src.exists():
                if not dry_run:
                    shutil.move(str(src), str(dst))
                verb = "[dry]" if dry_run else "MOVE"
                print(f"  {verb} {gid}/{fid}.png → gallery/{fid}.png")
                moved += 1
            elif dst.exists():
                print(f"  SKIP (already in gallery): {fid}.png")
            else:
                print(f"  MISSING: {gid}/{fid}.png ({name})")
                missing += 1

            new_items.append({
                "fid": fid,
                "name": name,
                "batch": "legacy",
                "old_group": label,
            })

    new_catalog = {"items": new_items}

    print(f"\nMoved: {moved} | Missing: {missing} | Total entries: {len(new_items)}")

    if not dry_run:
        save_catalog(new_catalog)
        print("catalog.json rewritten (new format).")
        # Clean up empty gid directories
        for group in old_catalog["groups"]:
            gid_dir = PROJ_DIR / group["gid"]
            if gid_dir.exists() and not any(gid_dir.iterdir()):
                gid_dir.rmdir()
                print(f"  Removed empty dir: {group['gid']}/")
    else:
        print("[dry-run] No files moved, catalog not changed.")


# ── Entry point ───────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args

    if "--migrate-old" in args:
        cmd_migrate_old(dry)
    elif "--check" in args:
        cmd_check()
    else:
        cmd_sync(dry)
        cmd_check()


if __name__ == "__main__":
    main()
