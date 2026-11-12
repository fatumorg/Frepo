#!/usr/bin/env bash
set -euo pipefail

out=$(cd "$1" && pwd)
. "$out/frepo.env"

export PACKAGER="naxce <naxcehelltea@gmail.com>"
export DEBIAN_FRONTEND=noninteractive

fetch_source() {
    tarball="$out/$(basename "$URL")"
    curl -fsSL -o "$tarball" "$URL"
    got=$(sha256sum "$tarball" | cut -d' ' -f1)
    if [ "$got" != "$SHA256" ]; then
        echo "sha256 mismatch for $URL" >&2
        exit 1
    fi
}

fetch_deps() {
    [ -n "$NEEDS" ] || return 0
    mkdir -p "$out/deps"
    if [ -z "$(ls -A "$out/deps")" ]; then
        python3 -I "$(dirname "$0")/frepo.py" fetch-dep "$NEEDS" "$TARGET" "$out/deps"
    fi
}

build_arch() {
    pacman -Syu --noconfirm base-devel git sudo
    fetch_deps
    if [ -n "$NEEDS" ]; then pacman -U --noconfirm "$out"/deps/*.pkg.tar.zst; fi
    id builder >/dev/null 2>&1 || useradd -m builder
    echo 'builder ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/builder
    work=/home/builder/build
    rm -rf "$work"
    mkdir -p "$work"
    cp "$out/PKGBUILD" "$work/"
    chown -R builder: "$work"
    cd "$work"
    sudo -u builder env PACKAGER="$PACKAGER" makepkg -s --noconfirm
    cp "$work"/*.pkg.tar.zst "$out/dist/"
}

build_deb() {
    apt-get update
    apt-get install -y --no-install-recommends build-essential dpkg-dev fakeroot
    fetch_deps
    if [ -n "$NEEDS" ]; then apt-get install -y "$out"/deps/*.deb; fi
    rm -rf "$out/src"
    mkdir -p "$out/src"
    tar -xzf "$tarball" -C "$out/src" --strip-components=1
    cp -r "$out/debian" "$out/src/debian"
    cd "$out/src"
    apt-get build-dep -y ./
    dpkg-buildpackage -us -uc -b
    cp "$out"/*.deb "$out/dist/"
}

build_fedora() {
    dnf -y install rpm-build 'dnf-command(builddep)'
    fetch_deps
    if [ -n "$NEEDS" ]; then dnf -y install "$out"/deps/*.rpm; fi
    top="$out/rpmbuild"
    defs=(--define "_topdir $top" --define "_sourcedir $out")
    mkdir -p "$top"
    dnf -y builddep "${defs[@]}" "$out/$PKG.spec"
    for _ in 1 2 3 4 5; do
        rm -f "$top"/SRPMS/*.buildreqs.nosrc.rpm
        if rpmbuild -bb "${defs[@]}" "$out/$PKG.spec"; then
            break
        fi
        dnf -y builddep "$top"/SRPMS/*.buildreqs.nosrc.rpm
    done
    test -n "$(find "$top/RPMS" -name '*.rpm')"
    find "$top/RPMS" -name '*.rpm' -exec cp {} "$out/dist/" \;
}

build_void() {
    xbps-install -Syu xbps
    xbps-install -yu
    xbps-install -y bash curl git sudo
    id builder >/dev/null 2>&1 || useradd -G xbuilder -m builder
    work=/home/builder/void-packages
    rm -rf "$work"
    sudo -u builder git clone --depth 1 https://github.com/void-linux/void-packages "$work"
    mkdir -p "$work/srcpkgs/$PKG"
    cp "$out/template" "$work/srcpkgs/$PKG/template"
    if [ -n "$NEEDS" ]; then
        fetch_deps
        mkdir -p "$work/hostdir/binpkgs"
        cp "$out"/deps/*.xbps "$work/hostdir/binpkgs/"
        xbps-rindex -a "$work"/hostdir/binpkgs/*.xbps
    fi
    chown -R builder: "$work"
    printf '%s\n' XBPS_CHROOT_CMD=uchroot >> "$work/etc/conf"
    cd "$work"
    sudo -u builder ./xbps-src binary-bootstrap
    sudo -u builder ./xbps-src pkg "$PKG"
    cp hostdir/binpkgs/"$PKG"-*.xbps "$out/dist/"
}

fetch_source
rm -rf "$out/dist"
mkdir -p "$out/dist"
case "$TARGET" in
    arch) build_arch ;;
    debian | ubuntu) build_deb ;;
    fedora) build_fedora ;;
    void) build_void ;;
    *) echo "unknown target $TARGET" >&2; exit 1 ;;
esac
ls -l "$out/dist"
