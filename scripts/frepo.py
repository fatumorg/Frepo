#!/usr/bin/env python3
import argparse
import os
import re

TARGETS = ("arch", "debian", "ubuntu", "fedora", "void")
BASE_URL = os.environ.get("FREPO_BASE_URL", "https://fatumorg.github.io/Frepo")

TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)(?:-beta([1-9]\d*))?$")


def parse_tag(tag):
    m = TAG_RE.match(tag)
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


def main(argv=None):
    parser = argparse.ArgumentParser(prog="frepo")
    parser.add_subparsers(dest="command")
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
