#!/usr/bin/env bash
set -euo pipefail

mkdir -p "$1"
site=$(cd "$1" && pwd)
root=$(cd "$(dirname "$0")/.." && pwd)
base=${FREPO_BASE_URL:-https://fatumorg.github.io/Frepo}

umask 077
keys=$(mktemp -d)
trap 'rm -rf "$keys"' EXIT
printf '%s\n' "$FREPO_NIX_KEY" > "$keys/secret"
pub=$(nix key convert-secret-to-public < "$keys/secret")
umask 022

names=$(nix eval --raw "$root#packages.x86_64-linux" --apply 'p: builtins.concatStringsSep " " (builtins.attrNames p)')
outs=()
for name in $names; do
    while read -r out; do
        outs+=("$out")
    done < <(nix build --no-link --print-out-paths \
        --extra-substituters "$base/nix" \
        --extra-trusted-public-keys "$pub" \
        "$root#$name")
done

mkdir -p "$site/nix"
nix copy --to "file://$site/nix?compression=zstd&secret-key=$keys/secret" "${outs[@]}"

printf 'StoreDir: /nix/store\nWantMassQuery: 1\nPriority: 50\n' > "$site/nix/nix-cache-info"
