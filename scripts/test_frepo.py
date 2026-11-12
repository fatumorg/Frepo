import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import re
import shlex

from frepo import ROOT, TARGETS, apply_bump, artifact_key, bump, fetch_dep, hash_path, matrix, parse_tag, readme_commands, render, resolve, select, site, smokes, target_version


class Rules(unittest.TestCase):
    def test_parse_tag(self):
        self.assertEqual(parse_tag("v1.7.0-beta1"), ("1.7.0", 1))
        self.assertEqual(parse_tag("v1.6.0"), ("1.6.0", None))
        for bad in ("1.7.0", "v1.7.0-b1", "v1.7.0-beta0", "v1.7", "v1.7.0-beta", "v1.7.0.b1", "v1.7.0\n"):
            with self.assertRaises(ValueError):
                parse_tag(bad)

    def test_target_version(self):
        self.assertEqual(target_version("1.7.0-beta1", "arch"), "1.7.0beta1")
        self.assertEqual(target_version("1.7.0-beta1", "void"), "1.7.0beta1")
        self.assertEqual(target_version("1.7.0-beta1", "debian"), "1.7.0~beta1")
        self.assertEqual(target_version("1.7.0-beta1", "ubuntu"), "1.7.0~beta1")
        self.assertEqual(target_version("1.7.0-beta1", "fedora"), "1.7.0~beta1")
        self.assertEqual(target_version("1.6.0", "debian"), "1.6.0")
        with self.assertRaises(ValueError):
            target_version("1.6.0", "gentoo")

    def test_resolve_beta_falls_back_to_stable(self):
        data = {"stable": {"version": "1.6.0"}, "beta": None}
        self.assertEqual(resolve(data, "beta"), {"version": "1.6.0"})

    def test_stable_bump_clears_older_beta(self):
        data = {"stable": {"version": "1.6.0"}, "beta": {"version": "1.7.0-beta3"}}
        out = apply_bump(data, {"version": "1.7.0"}, beta=False)
        self.assertIsNone(out["beta"])
        self.assertEqual(data["beta"], {"version": "1.7.0-beta3"})

    def test_stable_hotfix_keeps_newer_beta(self):
        data = {"stable": {"version": "1.7.0"}, "beta": {"version": "1.8.0-beta1"}}
        self.assertEqual(apply_bump(data, {"version": "1.7.1"}, beta=False)["beta"], {"version": "1.8.0-beta1"})

    def test_artifact_key(self):
        self.assertEqual(artifact_key("sylvaris", {"version": "1.6.0", "sha256": "abcdef0123456789"}), "sylvaris-1.6.0-abcdef01")


def entry(version, **extra):
    return {"tag": "v" + version, "version": version, "hash": "h", "sha256": "s", **extra}


class Bump(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src = self.root / "src"
        (self.src / "stack").mkdir(parents=True)
        (self.src / "stack" / "CMakeLists.txt").write_text("project(sylstack VERSION 1.0.1 LANGUAGES C CXX)\n")
        self.sub = hash_path(self.src / "stack")
        self.write("fatest", {"repo": "o/FaTest", "stable": entry("2.1.0"), "beta": None})
        self.write("sylvaris", {"repo": "o/Sylvaris", "stable": entry("1.5.0"), "beta": None})
        self.write("sylstack", {"repo": "o/Sylvaris", "follows": "sylvaris", "subdir": "stack", "stable": entry("1.0.1", subhash=self.sub), "beta": None})

    def write(self, name, data):
        d = self.root / "pkgs" / "by-name" / name[:2] / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "version.json").write_text(json.dumps(data, indent=2) + "\n")

    def path(self, name):
        return self.root / "pkgs" / "by-name" / name[:2] / name / "version.json"

    def fetch(self, repo, tag):
        return {"hash": "H", "sha256": "S", "path": str(self.src)}

    def test_bump_rejects_bad_tag(self):
        before = self.path("fatest").read_bytes()
        with self.assertRaises(ValueError):
            bump("fatest", "v2.1", self.fetch, self.root)
        self.assertEqual(self.path("fatest").read_bytes(), before)

    def test_bump_sylvaris_keeps_sylstack_when_stack_same(self):
        before = self.path("sylstack").read_bytes()
        self.assertEqual(bump("sylvaris", "v1.6.0", self.fetch, self.root), ["sylvaris"])
        self.assertEqual(self.path("sylstack").read_bytes(), before)
        self.assertEqual(json.loads(self.path("sylvaris").read_text())["stable"]["version"], "1.6.0")

    def test_bump_sylvaris_fails_when_stack_changed_same_version(self):
        data = json.loads(self.path("sylstack").read_text())
        data["stable"]["subhash"] = "sha256-other"
        self.write("sylstack", data)
        before = {n: self.path(n).read_bytes() for n in ("sylvaris", "sylstack")}
        with self.assertRaises(SystemExit):
            bump("sylvaris", "v1.6.0", self.fetch, self.root)
        self.assertEqual({n: self.path(n).read_bytes() for n in before}, before)

    def test_bump_sylvaris_moves_sylstack_when_version_raised(self):
        (self.src / "stack" / "CMakeLists.txt").write_text("project(sylstack VERSION 1.1.0 LANGUAGES C CXX)\n")
        self.assertEqual(bump("sylvaris", "v1.7.0", self.fetch, self.root), ["sylvaris", "sylstack"])
        stack = json.loads(self.path("sylstack").read_text())["stable"]
        self.assertEqual((stack["version"], stack["tag"], stack["sha256"]), ("1.1.0", "v1.7.0", "S"))

    def test_bump_beta_tag_sets_beta_only(self):
        bump("fatest", "v2.2.0-beta1", self.fetch, self.root)
        data = json.loads(self.path("fatest").read_text())
        self.assertEqual(data["beta"]["version"], "2.2.0-beta1")
        self.assertEqual(data["stable"]["version"], "2.1.0")


class Render(unittest.TestCase):
    def test_render_replaces_all_placeholders(self):
        for target in TARGETS:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                render("fatest", "stable", target, Path(tmp))
                for f in Path(tmp).rglob("*"):
                    if f.is_file():
                        self.assertIsNone(re.search(r"@[a-z0-9]+@", f.read_text()), f)
                env = dict(shlex.split(l)[0].split("=", 1) for l in (Path(tmp) / "frepo.env").read_text().splitlines())
                self.assertRegex(env["KEY"], r"^fatest-2\.1\.0-[0-9a-f]{8}$")
                self.assertEqual(env["PKG"], "fatest")
                self.assertEqual(env["TARGET"], target)
                self.assertEqual(env["SMOKE"], "fatest --version")
                self.assertEqual(env["URL"], "https://github.com/fatumorg/FaTest/archive/refs/tags/v2.1.0.tar.gz")
                self.assertRegex(env["SHA256"], r"^[0-9a-f]{64}$")

    def test_render_needs_and_placeholders_for_stack(self):
        for name, needs in (("sylstack", ""), ("sylvaris", "sylstack-1.0.1-7a0cfc8e")):
            for target in ("arch", "ubuntu", "fedora", "void"):
                with self.subTest(name=name, target=target), tempfile.TemporaryDirectory() as tmp:
                    render(name, "stable", target, Path(tmp))
                    for f in Path(tmp).rglob("*"):
                        if f.is_file():
                            self.assertIsNone(re.search(r"@[a-z0-9]+@", f.read_text()), f)
                    env = dict(shlex.split(l)[0].split("=", 1) for l in (Path(tmp) / "frepo.env").read_text().splitlines())
                    self.assertEqual(env["NEEDS"], needs)

    def test_render_recipe_files(self):
        expected = {"arch": "PKGBUILD", "void": "template", "fedora": "fatest.spec", "debian": "debian/control", "ubuntu": "debian/control"}
        for target, name in expected.items():
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                render("fatest", "stable", target, Path(tmp))
                self.assertTrue((Path(tmp) / name).is_file())


class Matrix(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.write("alpha", {"repo": "o/Alpha", "smoke": "a", "stable": entry("1.0.0"), "beta": None})
        self.write("bravo", {"repo": "o/Bravo", "smoke": "b", "skip": ["debian"], "stable": entry("1.0.0"), "beta": entry("1.1.0-beta1")})

    def write(self, name, data):
        d = self.root / "pkgs" / "by-name" / name[:2] / name
        d.mkdir(parents=True)
        (d / "version.json").write_text(json.dumps(data))
        for recipe in ("PKGBUILD", "template", name + ".spec", "debian"):
            (d / recipe).write_text("")

    def test_matrix_leaves_out_packages_without_recipes(self):
        self.write("charlie", {"repo": "o/Charlie", "smoke": "c", "stable": entry("1.0.0"), "beta": None})
        for f in (self.root / "pkgs" / "by-name" / "ch" / "charlie").glob("*"):
            if f.name != "version.json":
                f.unlink()
        self.assertNotIn("charlie", {r["pkg"] for r in matrix(self.root)["include"]})

    def test_matrix_skips_and_dedupes(self):
        rows = matrix(self.root)["include"]
        alpha = [r for r in rows if r["pkg"] == "alpha"]
        self.assertEqual(sorted(r["target"] for r in alpha), sorted(TARGETS))
        bravo = [r for r in rows if r["pkg"] == "bravo"]
        self.assertNotIn("debian", {r["target"] for r in bravo})
        self.assertEqual(len(bravo), 2 * 4)
        self.assertEqual(len({(r["key"], r["target"]) for r in rows}), len(rows))
        self.assertEqual({r["image"] for r in alpha if r["target"] == "fedora"}, {"fedora:45"})

    def test_matrix_orders_dependents_after_their_dependency(self):
        self.write("delta", {"repo": "o/Delta", "smoke": "d", "needs": "bravo", "stable": entry("2.0.0"), "beta": None})
        rows = matrix(self.root)["include"]
        delta = {r["target"]: r["needs"] for r in rows if r["pkg"] == "delta"}
        self.assertEqual(delta["arch"], artifact_key("bravo", entry("1.0.0")))
        self.assertEqual(delta["debian"], "")
        first = matrix(self.root, stage=0)["include"]
        second = matrix(self.root, stage=1)["include"]
        self.assertNotIn("delta", {r["pkg"] for r in first if r["target"] != "debian"})
        self.assertEqual({r["pkg"] for r in second}, {"delta"})
        self.assertEqual(len(first) + len(second), len(rows))
        self.assertTrue(all(r["needs"] for r in second))

    def test_matrix_missing_uses_injected_lookup(self):
        have = {"alpha-1.0.0-s": ["arch--alpha.pkg.tar.zst", "void--alpha.xbps"]}
        rows = matrix(self.root, missing=True, assets=lambda key: have.get(key, []))["include"]
        alpha = {r["target"] for r in rows if r["pkg"] == "alpha"}
        self.assertEqual(alpha, {"debian", "ubuntu", "fedora"})
        self.assertEqual(len([r for r in rows if r["pkg"] == "bravo"]), 8)


class Select(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name, extra in (("alpha", {}), ("bravo", {"skip": ["debian"]})):
            d = self.root / "pkgs" / "by-name" / name[:2] / name
            d.mkdir(parents=True)
            (d / "version.json").write_text(json.dumps({"repo": "o/x", "smoke": "s", "stable": entry("1.0.0"), "beta": None, **extra}))
            for recipe in ("PKGBUILD", "template", name + ".spec", "debian"):
                (d / recipe).write_text("")

    def test_select_lists_both_channels(self):
        rows = select("arch", self.root)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0][0], "stable")
        self.assertEqual(rows[0][1], rows[1][1])
        self.assertEqual({c for c, _ in rows}, {"stable", "beta"})

    def test_select_leaves_out_skipped(self):
        self.assertEqual(len(select("debian", self.root)), 2)


class Site(unittest.TestCase):
    def test_site_has_every_target_snippet(self):
        with tempfile.TemporaryDirectory() as tmp:
            site(tmp, "https://example.org/r")
            page = (Path(tmp) / "index.html").read_text()
        for part in ("/arch/$repo/$arch", "/deb", "/rpm/fedora/$releasever/frepo/x86_64", "/void/current", "/nix", "frepo-beta", "https://example.org/r/frepo.asc"):
            self.assertIn(part, page)
        self.assertNotIn("<script", page)


class Recipes(unittest.TestCase):
    def test_recipes_have_no_comments(self):
        for f in sorted((ROOT / "pkgs").rglob("*")):
            if f.is_file() and f.name != "version.json":
                for n, line in enumerate(f.read_text().splitlines(), 1):
                    if re.match(r"\s*#", line) and not (n == 1 and line.startswith("#!")):
                        self.fail(f"{f}:{n} has a comment")


class FetchDep(unittest.TestCase):
    def test_fetch_dep_downloads_only_matching_target_assets(self):
        release = {"assets": [
            {"name": "arch--sylstack-1.0.1-1-x86_64.pkg.tar.zst", "browser_download_url": "u1"},
            {"name": "fedora--sylstack-1.0.1-1.x86_64.rpm", "browser_download_url": "u2"},
        ]}
        urls = []
        with tempfile.TemporaryDirectory() as tmp:
            saved = []
            got = fetch_dep("k", "arch", Path(tmp) / "deps", "o/r", get=lambda u: urls.append(u) or release, save=lambda u, d: saved.append((u, d.name)))
        self.assertEqual(urls, ["https://api.github.com/repos/o/r/releases/tags/k"])
        self.assertEqual(saved, [("u1", "sylstack-1.0.1-1-x86_64.pkg.tar.zst")])
        self.assertEqual(got, ["sylstack-1.0.1-1-x86_64.pkg.tar.zst"])

    def test_fetch_dep_fails_without_asset(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(SystemExit):
            fetch_dep("k", "void", tmp, "o/r", get=lambda u: {"assets": []}, save=lambda u, d: None)


class Readme(unittest.TestCase):
    def test_readme_commands_present(self):
        for target in TARGETS:
            for channel in ("stable", "beta"):
                with self.subTest(target=target, channel=channel):
                    self.assertTrue(readme_commands(target, channel).strip())

    def test_beta_blocks_use_beta_repo(self):
        for target in TARGETS:
            self.assertIn("beta", readme_commands(target, "beta"))
            self.assertNotIn("beta", readme_commands(target, "stable"))

    def test_smokes_skip_unbuildable(self):
        self.assertNotIn("sylvaris", [n for n, _ in smokes("debian")])
        self.assertIn("sylvaris", [n for n, _ in smokes("arch")])


def run(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def cmp_pacman(a, b):
    return int(run("vercmp", a, b).stdout.strip())


def cmp_xbps(a, b):
    code = run("xbps-uhelper", "cmpver", a + "_1", b + "_1").returncode
    return {255: -1, 0: 0, 1: 1}[code]


def cmp_dpkg(a, b):
    if run("dpkg", "--compare-versions", a, "lt", b).returncode == 0:
        return -1
    if run("dpkg", "--compare-versions", a, "eq", b).returncode == 0:
        return 0
    return 1


def cmp_rpm(a, b):
    out = run("rpm", "--eval", '%{lua: print(rpm.vercmp("' + a + '", "' + b + '"))}')
    return int(out.stdout.strip())


COMPARE = {
    "arch": cmp_pacman,
    "void": cmp_xbps,
    "debian": cmp_dpkg,
    "ubuntu": cmp_dpkg,
    "fedora": cmp_rpm,
}


@unittest.skipUnless(os.environ.get("FREPO_REAL_TOOLS") == "1", "FREPO_REAL_TOOLS not set")
class RealTools(unittest.TestCase):
    def test_ordering(self):
        for target in TARGETS:
            cmp = COMPARE[target]
            tv = lambda v: target_version(v, target)
            with self.subTest(target=target):
                self.assertEqual(cmp(tv("1.7.0-beta1"), tv("1.7.0")), -1)
                self.assertEqual(cmp(tv("1.7.0-beta2"), tv("1.7.0-beta10")), -1)
                self.assertEqual(cmp(tv("1.7.0-beta1"), tv("1.6.9")), 1)


if __name__ == "__main__":
    unittest.main()
