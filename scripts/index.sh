#!/usr/bin/env bash
set -euo pipefail

target=$1
mkdir -p "$2"
site=$(cd "$2" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
signer="naxce <naxcehelltea@gmail.com>"
export DEBIAN_FRONTEND=noninteractive

umask 077
keys=$(mktemp -d)
export GNUPGHOME=$keys/gnupg
mkdir -m 700 "$GNUPGHOME"
cleanup() {
    gpgconf --kill gpg-agent 2>/dev/null || true
    rm -rf "$keys"
}
trap cleanup EXIT

import_gpg() {
    printf '%s' "$FREPO_GPG_KEY" | gpg --batch --quiet --import
    fpr=$(gpg --list-secret-keys --with-colons | awk -F: '/^fpr:/ {print $10; exit}')
}

fetch() {
    python3 -I "$here/frepo.py" select "$target" | while read -r channel key; do
        python3 -I "$here/frepo.py" fetch-dep "$key" "$target" "$(dest "$channel")"
    done
}

dest() {
    case "$target:$1" in
        arch:stable) echo "$site/arch/frepo/x86_64" ;;
        arch:beta) echo "$site/arch/frepo-beta/x86_64" ;;
        debian:stable | ubuntu:stable) echo "$site/deb/pool/$codename" ;;
        debian:beta | ubuntu:beta) echo "$site/deb/pool/$codename-beta" ;;
        fedora:stable) echo "$site/rpm/fedora/$release/frepo/x86_64" ;;
        fedora:beta) echo "$site/rpm/fedora/$release/frepo-beta/x86_64" ;;
        void:stable) echo "$site/void/current" ;;
        void:beta) echo "$site/void/beta" ;;
    esac
}

flatten_links() {
    find "$site" -type l -exec sh -c 'cp --remove-destination "$(readlink -f "$1")" "$1"' _ {} \;
}

index_arch() {
    for name in frepo frepo-beta; do
        dir=$site/arch/$name/x86_64
        [ -d "$dir" ] || continue
        cd "$dir"
        for f in *.pkg.tar.zst; do
            gpg --batch --yes --detach-sign "$f"
        done
        repo-add --sign --key "$fpr" "$name.db.tar.gz" ./*.pkg.tar.zst
    done
}

index_deb() {
    apt-get update
    apt-get install -y --no-install-recommends apt-utils gnupg gzip
    cd "$site/deb"
    for suite in "$codename" "$codename-beta"; do
        [ -d "pool/$suite" ] || continue
        bin=dists/$suite/main/binary-amd64
        mkdir -p "$bin"
        apt-ftparchive packages "pool/$suite" > "$bin/Packages"
        gzip -9nk -f "$bin/Packages"
        apt-ftparchive \
            -o "APT::FTPArchive::Release::Origin=frepo" \
            -o "APT::FTPArchive::Release::Suite=$suite" \
            -o "APT::FTPArchive::Release::Codename=$suite" \
            -o "APT::FTPArchive::Release::Components=main" \
            release "dists/$suite" > "$keys/Release"
        cp "$keys/Release" "dists/$suite/Release"
        gpg --batch --yes --clearsign -o "dists/$suite/InRelease" "dists/$suite/Release"
        gpg --batch --yes --armor --detach-sign -o "dists/$suite/Release.gpg" "dists/$suite/Release"
    done
}

index_fedora() {
    dnf -y install rpm-sign createrepo_c gnupg2
    for name in frepo frepo-beta; do
        dir=$site/rpm/fedora/$release/$name/x86_64
        [ -d "$dir" ] || continue
        cd "$dir"
        rpmsign --define "_gpg_name $fpr" --addsign ./*.rpm
        createrepo_c .
        gpg --batch --yes --detach-sign --armor -o repodata/repomd.xml.asc repodata/repomd.xml
    done
}

index_void() {
    printf '%s\n' "$FREPO_XBPS_KEY" > "$keys/key.pem"
    for name in current beta; do
        dir=$site/void/$name
        [ -d "$dir" ] || continue
        cd "$dir"
        xbps-rindex -a ./*.xbps
        xbps-rindex --sign --signedby "$signer" --privkey "$keys/key.pem" .
        xbps-rindex --sign-pkg --privkey "$keys/key.pem" ./*.xbps
    done
}

. /etc/os-release
codename=${VERSION_CODENAME:-}
release=${VERSION_ID:-}
case "$target" in
    arch) import_gpg; fetch; index_arch ;;
    debian | ubuntu) apt-get update; apt-get install -y --no-install-recommends gnupg; import_gpg; fetch; index_deb ;;
    fedora) dnf -y install gnupg2; import_gpg; fetch; index_fedora ;;
    void) fetch; index_void ;;
    *) echo "unknown target $target" >&2; exit 1 ;;
esac
flatten_links
umask 022
find "$site" -type d -exec chmod 755 {} +
find "$site" -type f -exec chmod 644 {} +
