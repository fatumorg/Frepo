#!/usr/bin/env bash
set -euo pipefail

out=$(cd "$1" && pwd)
. "$out/frepo.env"
dist="$out/dist"
export DEBIAN_FRONTEND=noninteractive

smoke_arch() {
    (cd "$dist" && repo-add frepo.db.tar.gz ./*.pkg.tar.zst)
    printf '[frepo]\nSigLevel = Never\nServer = file://%s\n' "$dist" >> /etc/pacman.conf
    pacman -Sy --noconfirm "$PKG"
}

smoke_deb() {
    apt-get install -y --no-install-recommends dpkg-dev
    (cd "$dist" && dpkg-scanpackages . /dev/null > Packages)
    echo "deb [trusted=yes] file:$dist ./" > /etc/apt/sources.list.d/frepo.list
    apt-get update
    apt-get install -y "$PKG"
}

smoke_fedora() {
    dnf -y install createrepo_c
    createrepo_c "$dist"
    printf '[frepo]\nname=frepo\nbaseurl=file://%s\nenabled=1\ngpgcheck=0\n' "$dist" > /etc/yum.repos.d/frepo.repo
    dnf -y install "$PKG"
}

smoke_void() {
    xbps-rindex -a "$dist"/*.xbps
    xbps-install -y -S -R "$dist" "$PKG"
}

case "$TARGET" in
    arch) smoke_arch ;;
    debian | ubuntu) smoke_deb ;;
    fedora) smoke_fedora ;;
    void) smoke_void ;;
    *) echo "unknown target $TARGET" >&2; exit 1 ;;
esac

sh -c "$SMOKE"
