#!/usr/bin/env python3
"""Archive old run artifacts under data/ into monthly tar.gz files.

Dry run by default: prints what would be archived.  With ``--apply`` it

  1. writes ``data/_archive/<YYYY-MM>.tar.gz`` from the selected files,
  2. re-reads every member and compares its sha256 with the original file,
  3. deletes the originals only for archives that verified completely,
  4. records the member list (name, size, mtime, sha256) in
     ``data/_archive/INDEX.json``,
  5. marks the matching entries in ``data/runs_index.json`` with the archive
     path, so a single run can still be read without extracting anything:

         tar -xOf data/_archive/2026-09.tar.gz <member name>

Never touched: git-tracked files, the run record (manifest/runmeta/result),
source files (py/sh/ps1/html/md/txt), and anything named in a test file.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from build_runs_index import split_name  # noqa: E402

RECORD_KINDS = {"manifest.json", "runmeta.json", "result.json"}
SOURCE_EXT = {".py", ".sh", ".ps1", ".html", ".md", ".txt", ".yml", ".yaml",
              ".toml", ".cfg", ".pyc"}
SKIP_DIRS = {"__pycache__", "_archive", "analysis"}


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def tracked_files(repo_root):
    out = subprocess.run(["git", "-C", repo_root, "ls-files", "-z", "data"],
                         capture_output=True, check=True).stdout
    return {p for p in out.decode("utf-8", "replace").split("\0") if p}


def test_referenced(paths):
    """Base names that any test_*.py mentions literally."""
    names = set()
    for path in paths:
        with open(path, encoding="utf-8", errors="replace") as f:
            for m in re.finditer(r"data/[A-Za-z0-9_.\-]+", f.read()):
                names.add(os.path.basename(m.group(0)))
    return names


def select(data_dir, cutoff, tracked, protected):
    picked, skipped = [], []
    for root, dirs, files in os.walk(data_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in sorted(files):
            full = os.path.join(root, name)
            rel = os.path.relpath(full, data_dir)
            st = os.stat(full)
            if st.st_mtime >= cutoff:
                skipped.append((rel, "recent"))
                continue
            if "data/" + rel in tracked:
                skipped.append((rel, "tracked"))
                continue
            if name in protected:
                skipped.append((rel, "test-fixture"))
                continue
            parsed = split_name(name)
            if parsed is None:
                skipped.append((rel, "not-an-artifact"))
                continue
            kind = parsed[3]
            if kind.split("/")[-1] in RECORD_KINDS:
                skipped.append((rel, "record"))
                continue
            if os.path.splitext(name)[1].lower() in SOURCE_EXT:
                skipped.append((rel, "source"))
                continue
            if name.startswith("enemies_"):
                skipped.append((rel, "enemy-data"))
                continue
            picked.append({"rel": rel, "name": name, "bytes": st.st_size,
                           "mtime": int(st.st_mtime),
                           "month": time.strftime("%Y-%m", time.localtime(st.st_mtime))})
    return picked, skipped


def tar_supports_mac_metadata_flag():
    """bsdtar on macOS packs each file's xattrs into a sibling ._ entry; tell it
    not to, so the archive holds exactly the files we listed."""
    probe = subprocess.run(["tar", "--no-mac-metadata", "-cf", os.devnull,
                            "-T", os.devnull], capture_output=True)
    return probe.returncode == 0


def build_archive(data_dir, month, items, out_path):
    listing = out_path + ".list"
    with open(listing, "w", encoding="utf-8") as f:
        f.write("\n".join(it["rel"] for it in items) + "\n")
    tmp = out_path + ".tmp"
    cmd = ["tar", "-C", data_dir, "-czf", tmp]
    if tar_supports_mac_metadata_flag():
        cmd.append("--no-mac-metadata")
    cmd += ["-T", listing]
    subprocess.run(cmd, check=True)
    os.remove(listing)
    return tmp


def verify(data_dir, archive, items):
    """Every member must be present, with the original size and sha256."""
    want = {it["rel"]: it for it in items}
    seen = set()
    bad = []
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar:
            if member.name.startswith("._") and member.name not in want:
                continue  # AppleDouble/xattr sidecar; not part of the inventory
            it = want.get(member.name)
            if it is None:
                bad.append((member.name, "unexpected member"))
                continue
            seen.add(member.name)
            handle = tar.extractfile(member)
            h = hashlib.sha256()
            size = 0
            for block in iter(lambda: handle.read(1 << 20), b""):
                h.update(block)
                size += len(block)
            if size != it["bytes"]:
                bad.append((member.name, f"size {size} != {it['bytes']}"))
                continue
            digest = sha256_file(os.path.join(data_dir, it["rel"]))
            if digest != h.hexdigest():
                bad.append((member.name, "sha256 mismatch"))
    for name in want:
        if name not in seen:
            bad.append((name, "missing from archive"))
    return bad


def patch_runs_index(index_path, archive_path, members, data_dir=None):
    """Point runs_index.json entries at the archive they now live in."""
    if not os.path.exists(index_path):
        return 0
    with open(index_path, encoding="utf-8") as f:
        index = json.load(f)
    touched = 0
    by_path = {os.path.basename(m): archive_path for m in members}
    for run in index.get("runs", []):
        for kind, meta in run.get("files", {}).items():
            target = by_path.get(meta.get("path"))
            if target:
                meta["archived_to"] = target
                touched += 1
    index.setdefault("archives", {})[os.path.basename(archive_path)] = {
        "path": archive_path,
        "members": len(members),
        "bytes": os.path.getsize(archive_path),
    }
    tmp = index_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, index_path)
    return touched


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=HERE)
    ap.add_argument("--cutoff", default="2026-10-20",
                    help="archive artifacts last modified before this date")
    ap.add_argument("--apply", action="store_true", help="actually write and delete")
    ap.add_argument("--force", action="store_true", help="overwrite existing archives")
    args = ap.parse_args(argv)

    repo_root = os.path.dirname(HERE)
    cutoff = time.mktime(time.strptime(args.cutoff, "%Y-%m-%d"))
    archive_dir = os.path.join(args.dir, "_archive")
    tracked = tracked_files(repo_root)
    tests = [os.path.join(repo_root, f) for f in os.listdir(repo_root)
             if re.match(r"^test_.*\.py$", f)]
    protected = test_referenced(tests)

    picked, skipped = select(args.dir, cutoff, tracked, protected)
    by_month = {}
    for it in picked:
        by_month.setdefault(it["month"], []).append(it)
    total_bytes = sum(it["bytes"] for it in picked)

    print(f"cutoff {args.cutoff}: {len(picked)} files, {total_bytes/1e9:.2f} GB")
    for month in sorted(by_month):
        items = by_month[month]
        print(f"  {month}: {len(items):5d} files {sum(i['bytes'] for i in items)/1e6:8.1f} MB"
              f" -> data/_archive/{month}.tar.gz")
    reason = {}
    for _, why in skipped:
        reason[why] = reason.get(why, 0) + 1
    print("  skipped:", ", ".join(f"{k}={v}" for k, v in sorted(reason.items())))
    if not args.apply:
        print("dry run: nothing written (use --apply)")
        return 0

    os.makedirs(archive_dir, exist_ok=True)
    index_path = os.path.join(args.dir, "runs_index.json")
    records = {}
    deleted = kept = 0
    before = total_bytes
    for month in sorted(by_month):
        items = by_month[month]
        out = os.path.join(archive_dir, f"{month}.tar.gz")
        if os.path.exists(out) and not args.force:
            print(f"  {out} exists, refusing to overwrite (use --force)")
            continue
        tmp = build_archive(args.dir, month, items, out)
        problems = verify(args.dir, tmp, items)
        if problems:
            print(f"  {month}: verification FAILED, originals kept")
            for name, why in problems[:10]:
                print(f"    {name}: {why}")
            os.remove(tmp)
            continue
        os.replace(tmp, out)
        # verified: hash the archive once for the record, then drop originals
        archive_sha = sha256_file(out)
        members = {}
        for it in items:
            members[it["rel"]] = {"bytes": it["bytes"], "mtime": it["mtime"],
                                  "sha256": sha256_file(os.path.join(args.dir, it["rel"]))}
            os.remove(os.path.join(args.dir, it["rel"]))
            deleted += 1
        records[os.path.basename(out)] = {
            "path": os.path.relpath(out, repo_root),
            "sha256": archive_sha,
            "bytes": os.path.getsize(out),
            "members": members,
        }
        kept += patch_runs_index(index_path, os.path.relpath(out, repo_root),
                                 list(members), args.dir)
        print(f"  {month}: archived {len(items)} files -> {os.path.relpath(out, repo_root)}"
              f" ({os.path.getsize(out)/1e6:.1f} MB), originals deleted")

    # drop directories the deletion left empty (only below data/)
    for root, dirs, files in os.walk(args.dir, topdown=False):
        if os.path.abspath(root) == os.path.abspath(args.dir):
            continue
        if root.startswith(archive_dir):
            continue
        if not os.listdir(root):
            os.rmdir(root)

    index = {
        "generated": int(time.time()),
        "generated_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "cutoff": args.cutoff,
        "archives": records,
        "totals": {
            "files": sum(len(r["members"]) for r in records.values()),
            "original_bytes": before,
            "archive_bytes": sum(r["bytes"] for r in records.values()),
        },
        "restore": "tar -xzf <archive> <member>   # -O to stream instead of writing",
    }
    with open(os.path.join(archive_dir, "INDEX.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
        f.write("\n")

    print(f"deleted {deleted} files ({before/1e9:.2f} GB), "
          f"archives take {index['totals']['archive_bytes']/1e6:.1f} MB")
    print(f"index entries pointed at archives: {kept}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
