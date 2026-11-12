#!/usr/bin/env bash
set -euo pipefail

target=$1
channel=$2
here=$(cd "$(dirname "$0")" && pwd)
export DEBIAN_FRONTEND=noninteractive

sudo() { "$@"; }

install_pkg() {
    case "$target" in
        arch) pacman -S --needed --noconfirm "$1" ;;
        debian | ubuntu) apt-get install -y "$1" ;;
        fedora) dnf install -y "$1" ;;
        void) xbps-install -y "$1" ;;
    esac
}

for attempt in 1 2 3 4 5 6 7 8 9 10; do
    curl -fsS -o /dev/null "https://fatumorg.github.io/Frepo/frepo.asc" && break
    [ "$attempt" = 10 ] && exit 1
    sleep 15
done

cmds=$(python3 -I "$here/frepo.py" readme-commands "$target" "$channel")
bash -euxc "$(declare -f sudo); $cmds" < <(yes)

python3 -I "$here/frepo.py" smokes "$target" | while IFS=$'\t' read -r name smoke; do
    install_pkg "$name" < <(yes)
    bash -c "$smoke"
done
