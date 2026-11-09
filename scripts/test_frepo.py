import os
import subprocess
import unittest

from frepo import TARGETS, apply_bump, artifact_key, parse_tag, resolve, target_version


class Rules(unittest.TestCase):
    def test_parse_tag(self):
        self.assertEqual(parse_tag("v1.7.0-beta1"), ("1.7.0", 1))
        self.assertEqual(parse_tag("v1.6.0"), ("1.6.0", None))
        for bad in ("1.7.0", "v1.7.0-b1", "v1.7.0-beta0", "v1.7", "v1.7.0-beta", "v1.7.0.b1"):
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
