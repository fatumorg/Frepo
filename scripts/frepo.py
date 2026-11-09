#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path

TARGETS = ("arch", "debian", "ubuntu", "fedora", "void")
BASE_URL = os.environ.get("FREPO_BASE_URL", "https://fatumorg.github.io/Frepo")

ROOT = Path(__file__).resolve().parent.parent
TAG_RE = re.compile(r"v(\d+\.\d+\.\d+)(?:-beta([1-9]\d*))?")


def parse_tag(tag):
    m = TAG_RE.fullmatch(tag)
    if not m:
        raise ValueError(f"bad tag: {tag}")
    return m.group(1), int(m.group(2)) if m.group(2) else None


def nix_version(base, beta):
    return base if beta is None else f"{base}-beta{beta}"


def target_version(version, target):
    if target in ("arch", "void"):
        return version.replace("-beta", "beta")
    if target in ("debian", "ubuntu", "fedora"):
        return version.replace("-beta", "~beta")
    raise ValueError(f"unknown target: {target}")


def base_tuple(version):
    return tuple(int(x) for x in version.split("-")[0].split("."))


def is_newer(a, b):
    return base_tuple(a) > base_tuple(b)


def resolve(data, channel):
    if channel == "stable":
        return data["stable"]
    if channel == "beta":
        return data["beta"] or data["stable"]
    raise ValueError(f"unknown channel: {channel}")


def apply_bump(data, entry, beta):
    out = dict(data)
    if beta:
        out["beta"] = entry
        return out
    out["stable"] = entry
    cur = data.get("beta")
    if not (cur and is_newer(cur["version"], entry["version"])):
        out["beta"] = None
    return out


def artifact_key(name, entry):
    return f"{name}-{entry['version']}-{entry['sha256'][:8]}"


def package_dirs(root=ROOT):
    return {p.parent.name: p.parent for p in sorted(root.glob("pkgs/by-name/*/*/version.json"))}


def fetch_source(repo, tag):
    url = f"https://github.com/{repo}/archive/refs/tags/{tag}.tar.gz"
    out = subprocess.run(["nix", "flake", "prefetch", "--json", url], capture_output=True, text=True, check=True)
    info = json.loads(out.stdout)
    with urllib.request.urlopen(url) as r:
        sha = hashlib.sha256(r.read()).hexdigest()
    return {"hash": info["hash"], "sha256": sha, "path": info["storePath"]}


def hash_path(path):
    out = subprocess.run(["nix", "hash", "path", str(path)], capture_output=True, text=True, check=True)
    return out.stdout.strip()


def cmake_version(path):
    m = re.search(r"project\(sylstack VERSION (\d+\.\d+\.\d+)", (Path(path) / "stack" / "CMakeLists.txt").read_text())
    if not m:
        raise SystemExit("no sylstack version in stack/CMakeLists.txt")
    return m.group(1)


def follower_entry(name, data, src, tag, beta):
    cur = (data["beta"] or data["stable"]) if beta else data["stable"]
    sub = hash_path(Path(src["path"]) / data["subdir"])
    ver = cmake_version(src["path"])
    if cur and cur["subhash"] == sub:
        return None
    if cur and cur["version"].split("-")[0] == ver:
        raise SystemExit(f"{data['subdir']}/ changed but {name} is still {ver}: raise the version in Sylvaris first")
    base, n = parse_tag(tag)
    return {
        "tag": tag,
        "version": nix_version(ver, n),
        "hash": src["hash"],
        "sha256": src["sha256"],
        "subhash": sub,
    }


def bump(name, tag, fetch=fetch_source, root=ROOT):
    base, n = parse_tag(tag)
    dirs = package_dirs(root)
    datas = {k: json.loads((d / "version.json").read_text()) for k, d in dirs.items()}
    data = datas[name]
    src = fetch(data["repo"], tag)
    entry = {"tag": tag, "version": nix_version(base, n), "hash": src["hash"], "sha256": src["sha256"]}
    out = {name: apply_bump(data, entry, n is not None)}
    for k, d in datas.items():
        if d.get("follows") == name:
            e = follower_entry(k, d, src, tag, n is not None)
            if e:
                out[k] = apply_bump(d, e, n is not None)
    for k, d in out.items():
        (dirs[k] / "version.json").write_text(json.dumps(d, indent=2) + "\n")
    return list(out)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="frepo")
    sub = parser.add_subparsers(dest="command")
    b = sub.add_parser("bump")
    b.add_argument("package")
    b.add_argument("tag")
    args = parser.parse_args(argv)
    if args.command == "bump":
        print("\n".join(bump(args.package, args.tag)))
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
