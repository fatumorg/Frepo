#!/usr/bin/env python3
import argparse
import hashlib
import html
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import urllib.request
from email.utils import formatdate
from pathlib import Path

TARGETS = ("arch", "debian", "ubuntu", "fedora", "void")
BASE_URL = os.environ.get("FREPO_BASE_URL") or "https://fatumorg.github.io/Frepo"

GPG_FPR = "71F436240F5DECB80B527254129B59851248FCFA"
NIX_KEY = "frepo-1:gKWuz++daZePxuk4SUjIByC40ua1WCwAdU7zJPuRIKI="
MAINTAINER = "naxce <naxcehelltea@gmail.com>"
IMAGES = {
    "arch": "archlinux:latest",
    "debian": "debian:trixie",
    "ubuntu": "ubuntu:26.04",
    "fedora": "fedora:45",
    "void": "ghcr.io/void-linux/void-glibc-full:latest",
}
RECIPES = {"arch": "PKGBUILD", "void": "template", "fedora": "{pkg}.spec", "debian": "debian", "ubuntu": "debian"}

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


def buildable(pkgdir, data, name, target):
    return target not in data.get("skip", []) and (pkgdir / RECIPES[target].format(pkg=name)).exists()


def needs_key(dirs, data, channel, target):
    dep = data.get("needs")
    if not dep:
        return ""
    dep_data = json.loads((dirs[dep] / "version.json").read_text())
    ent = resolve(dep_data, channel)
    if not ent or not buildable(dirs[dep], dep_data, dep, target):
        return ""
    return artifact_key(dep, ent)


def render(name, channel, target, outdir, root=ROOT):
    dirs = package_dirs(root)
    pkgdir = dirs[name]
    data = json.loads((pkgdir / "version.json").read_text())
    ent = resolve(data, channel)
    if not ent:
        raise SystemExit(f"{name} has no {channel} release")
    tag = ent["tag"]
    repo = data["repo"]
    url = f"https://github.com/{repo}/archive/refs/tags/{tag}.tar.gz"
    subs = {
        "@pkgver@": target_version(ent["version"], target),
        "@url@": url,
        "@sha256@": ent["sha256"],
        "@srcdir@": f"{repo.split('/')[1]}-{tag[1:]}",
        "@maintainer@": MAINTAINER,
        "@date@": formatdate().replace("-0000", "+0000"),
    }
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    recipe = RECIPES[target].format(pkg=name)
    src = pkgdir / recipe
    dst = outdir / recipe
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
        files = [f for f in dst.rglob("*") if f.is_file()]
    else:
        shutil.copy2(src, dst)
        files = [dst]
    for f in files:
        text = f.read_text()
        for k, v in subs.items():
            text = text.replace(k, v)
        f.write_text(text)
    env = {
        "PKG": name,
        "TARGET": target,
        "KEY": artifact_key(name, ent),
        "URL": url,
        "SHA256": ent["sha256"],
        "SMOKE": data["smoke"],
        "NEEDS": needs_key(dirs, data, channel, target),
    }
    (outdir / "frepo.env").write_text("".join(f"{k}={shlex.quote(v)}\n" for k, v in env.items()))
    return env


def release_assets(key):
    out = subprocess.run(["gh", "release", "view", key, "--json", "assets"], capture_output=True, text=True)
    if out.returncode != 0:
        if "not found" in out.stderr.lower():
            return []
        raise SystemExit(f"gh release view {key} failed: {out.stderr.strip()}")
    return [a["name"] for a in json.loads(out.stdout)["assets"]]


def http_json(url):
    req = urllib.request.Request(url)
    token = os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def http_save(url, dst):
    with urllib.request.urlopen(url) as r, open(dst, "wb") as f:
        shutil.copyfileobj(r, f)


def fetch_dep(key, target, outdir, repo=None, get=http_json, save=http_save):
    repo = repo or os.environ["GITHUB_REPOSITORY"]
    prefix = target + "--"
    found = [a for a in get(f"https://api.github.com/repos/{repo}/releases/tags/{key}")["assets"] if a["name"].startswith(prefix)]
    if not found:
        raise SystemExit(f"release {key} has no {target} asset")
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    names = [a["name"][len(prefix):] for a in found]
    if target in ("debian", "ubuntu", "fedora"):
        names = [re.sub(r"\.beta(\d)", r"~beta\1", n) for n in names]
    for a, n in zip(found, names):
        save(a["browser_download_url"], outdir / n)
    return names


def matrix(root=ROOT, missing=False, assets=release_assets, stage=None):
    rows = {}
    dirs = package_dirs(root)
    for name, d in dirs.items():
        data = json.loads((d / "version.json").read_text())
        for channel in ("stable", "beta"):
            ent = resolve(data, channel)
            if not ent:
                continue
            key = artifact_key(name, ent)
            for target in TARGETS:
                if not buildable(d, data, name, target):
                    continue
                needs = needs_key(dirs, data, channel, target)
                rows.setdefault((key, target), {"pkg": name, "channel": channel, "target": target, "key": key, "needs": needs, "image": IMAGES[target]})
    out = list(rows.values())
    if stage is not None:
        out = [r for r in out if bool(r["needs"]) == bool(stage)]
    if missing:
        cache = {}
        out = [r for r in out if not any(a.startswith(r["target"] + "--") for a in cache.setdefault(r["key"], assets(r["key"])))]
    return {"include": out}


def select(target, root=ROOT):
    rows = []
    for name, d in package_dirs(root).items():
        data = json.loads((d / "version.json").read_text())
        if not buildable(d, data, name, target):
            continue
        for channel in ("stable", "beta"):
            ent = resolve(data, channel)
            if ent:
                rows.append((channel, artifact_key(name, ent)))
    return rows


def snippets(base):
    codename = "$(. /etc/os-release; echo $VERSION_CODENAME)"
    out = []

    def add(title, text):
        out.append(f"<h3>{html.escape(title)}</h3>\n<pre>{html.escape(text.strip())}</pre>")

    add("Arch", f"""
curl -fsS {base}/frepo.asc | sudo pacman-key --add -
sudo pacman-key --lsign-key {GPG_FPR}
append to /etc/pacman.conf, use [frepo-beta] for beta builds:
[frepo]
Server = {base}/arch/$repo/$arch
sudo pacman -Syu fatest
""")
    add("Debian", f"""
sudo install -d /etc/apt/keyrings
sudo curl -fsSo /etc/apt/keyrings/frepo.asc {base}/frepo.asc
echo "deb [signed-by=/etc/apt/keyrings/frepo.asc] {base}/deb trixie main" | sudo tee /etc/apt/sources.list.d/frepo.list
beta builds: suite trixie-beta instead of trixie
sudo apt update && sudo apt install fatest
""")
    add("Ubuntu", f"""
sudo install -d /etc/apt/keyrings
sudo curl -fsSo /etc/apt/keyrings/frepo.asc {base}/frepo.asc
echo "deb [signed-by=/etc/apt/keyrings/frepo.asc] {base}/deb {codename} main" | sudo tee /etc/apt/sources.list.d/frepo.list
beta builds: suite {codename}-beta instead
sudo apt update && sudo apt install fatest
""")
    add("Fedora", f"""
sudo tee /etc/yum.repos.d/frepo.repo <<'REPO'
[frepo]
name=frepo
baseurl={base}/rpm/fedora/$releasever/frepo/x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey={base}/frepo.asc
REPO
beta builds: section [frepo-beta] with baseurl {base}/rpm/fedora/$releasever/frepo-beta/x86_64
sudo dnf install fatest
""")
    add("Void", f"""
echo "repository={base}/void/current" | sudo tee /etc/xbps.d/frepo.conf
beta builds: repository={base}/void/beta
sudo xbps-install -S fatest
""")
    add("Nix", f"""
nix.settings.extra-substituters = [ "{base}/nix" ];
nix.settings.extra-trusted-public-keys = [ "{NIX_KEY}" ];
nix run github:fatumorg/Frepo#fatest
beta builds: github:fatumorg/Frepo#fatest-beta
""")
    return "\n".join(out)


def site(sitedir, base=BASE_URL):
    sitedir = Path(sitedir)
    sitedir.mkdir(parents=True, exist_ok=True)
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Frepo</title>
<style>body{{font-family:sans-serif;max-width:52rem;margin:2rem auto;padding:0 1rem}}pre{{overflow-x:auto;background:#eee;padding:.75rem}}@media(prefers-color-scheme:dark){{body{{background:#111;color:#ddd}}pre{{background:#222}}}}</style>
</head>
<body>
<h1>Frepo</h1>
<p>Packages by naxce for Arch, Debian, Ubuntu, Fedora, Void and Nix. Signing key fingerprint: {GPG_FPR}</p>
<h2>Beta</h2>
<p>Beta builds are the version being worked on right now and may have bugs. Enable either frepo or frepo-beta, never both.</p>
<h2>Install</h2>
{snippets(base)}
</body>
</html>
"""
    (sitedir / "index.html").write_text(page)
    key = os.environ.get("FREPO_GPG_KEY")
    if key:
        with tempfile.TemporaryDirectory() as home:
            env = {**os.environ, "GNUPGHOME": home}
            subprocess.run(["gpg", "--batch", "--quiet", "--import"], input=key, text=True, env=env, check=True)
            pub = subprocess.run(["gpg", "--armor", "--export", GPG_FPR], capture_output=True, text=True, env=env, check=True)
        if not pub.stdout:
            raise SystemExit("gpg exported no public key")
        (sitedir / "frepo.asc").write_text(pub.stdout)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="frepo")
    sub = parser.add_subparsers(dest="command")
    b = sub.add_parser("bump")
    b.add_argument("package")
    b.add_argument("tag")
    r = sub.add_parser("render")
    r.add_argument("package")
    r.add_argument("channel", choices=("stable", "beta"))
    r.add_argument("target", choices=TARGETS)
    r.add_argument("outdir")
    m = sub.add_parser("matrix")
    m.add_argument("--missing", action="store_true")
    m.add_argument("--stage", type=int, choices=(0, 1))
    f = sub.add_parser("fetch-dep")
    f.add_argument("key")
    f.add_argument("target", choices=TARGETS)
    f.add_argument("outdir")
    sl = sub.add_parser("select")
    sl.add_argument("target", choices=TARGETS)
    st = sub.add_parser("site")
    st.add_argument("sitedir")
    args = parser.parse_args(argv)
    if args.command == "bump":
        print("\n".join(bump(args.package, args.tag)))
    elif args.command == "render":
        render(args.package, args.channel, args.target, args.outdir)
    elif args.command == "matrix":
        print(json.dumps(matrix(missing=args.missing, stage=args.stage)))
    elif args.command == "fetch-dep":
        fetch_dep(args.key, args.target, args.outdir)
    elif args.command == "select":
        print("\n".join(f"{c} {k}" for c, k in select(args.target)))
    elif args.command == "site":
        site(args.sitedir)
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
