# Frepo

Frepo is a package repo for Linux projects written by naxce. It works next to the official repos of any distro (Arch, Debian, Ubuntu, Fedora, Void) and as a Nix flake.

## Packages

| Package | Version | Description |
| --- | --- | --- |
| fatest | — | A fast, clean terminal speedtest tool |
| tempinfocli | 0.3.0 | A live terminal temperature dashboard |
| sylstack | 1.0.1 | Small Qt Quick runtime for Wayland desktop shells, made for Sylvaris |
| sylvaris | 1.6.0 | Modular desktop shell for Hyprland, niri and sway, built on SylStack |
| codedesk | — | Desktop workspace for Claude Code |
| archon | — | Linux-native archive browser and mod tool for GTA V |

## Install

Add the repo, then install packages with the package manager of your distro. The signing key fingerprint is 71F436240F5DECB80B527254129B59851248FCFA.

### Arch

```sh
curl -fsS https://fatumorg.github.io/Frepo/frepo.asc | sudo pacman-key --add -
sudo pacman-key --lsign-key 71F436240F5DECB80B527254129B59851248FCFA
printf '[frepo]\nServer = https://fatumorg.github.io/Frepo/arch/$repo/$arch\n' | sudo tee -a /etc/pacman.conf
sudo pacman -Syu fatest
```

### Debian

```sh
sudo install -d /etc/apt/keyrings
sudo curl -fsSo /etc/apt/keyrings/frepo.asc https://fatumorg.github.io/Frepo/frepo.asc
echo "deb [signed-by=/etc/apt/keyrings/frepo.asc] https://fatumorg.github.io/Frepo/deb trixie main" | sudo tee /etc/apt/sources.list.d/frepo.list
sudo apt update
sudo apt install fatest
```

### Ubuntu

```sh
sudo install -d /etc/apt/keyrings
sudo curl -fsSo /etc/apt/keyrings/frepo.asc https://fatumorg.github.io/Frepo/frepo.asc
echo "deb [signed-by=/etc/apt/keyrings/frepo.asc] https://fatumorg.github.io/Frepo/deb $(. /etc/os-release; echo $VERSION_CODENAME) main" | sudo tee /etc/apt/sources.list.d/frepo.list
sudo apt update
sudo apt install fatest
```

### Fedora

```sh
sudo tee /etc/yum.repos.d/frepo.repo <<'REPO'
[frepo]
name=frepo
baseurl=https://fatumorg.github.io/Frepo/rpm/fedora/$releasever/frepo/x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://fatumorg.github.io/Frepo/frepo.asc
REPO
sudo dnf install fatest
```

### Void

```sh
sudo mkdir -p /etc/xbps.d
echo "repository=https://fatumorg.github.io/Frepo/void/current" | sudo tee /etc/xbps.d/frepo.conf
sudo xbps-install -S fatest
```

### Nix

Try a package without a flake input:

```sh
nix profile install github:fatumorg/Frepo#sylvaris
```

Use it as a flake input:

```nix
{
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  inputs.frepo = {
    url = "github:fatumorg/Frepo";
    inputs.nixpkgs.follows = "nixpkgs";
  };
}
```

Then pick packages from `inputs.frepo.packages.${system}`, where every `-beta` variant sits next to the stable package, or add an overlay. Pick one overlay, never both.

`overlays.default` gives the stable builds:

```nix
nixpkgs.overlays = [ inputs.frepo.overlays.default ];
```

`overlays.beta` gives the beta builds under the same names, so `pkgs.sylvaris` is the beta Sylvaris:

```nix
nixpkgs.overlays = [ inputs.frepo.overlays.beta ];
```

Sylvaris also ships `nixosModules.sylvaris` and `homeManagerModules.sylvaris`.

## Beta

Beta builds are the version being worked on right now; they may have bugs. Enable one or the other: the stable repo (`frepo`) or the beta repo (`frepo-beta`), never both. When a package has no beta, the beta repo carries its stable build.

### Arch

```sh
curl -fsS https://fatumorg.github.io/Frepo/frepo.asc | sudo pacman-key --add -
sudo pacman-key --lsign-key 71F436240F5DECB80B527254129B59851248FCFA
printf '[frepo-beta]\nServer = https://fatumorg.github.io/Frepo/arch/$repo/$arch\n' | sudo tee -a /etc/pacman.conf
sudo pacman -Syu fatest
```

### Debian

```sh
sudo install -d /etc/apt/keyrings
sudo curl -fsSo /etc/apt/keyrings/frepo.asc https://fatumorg.github.io/Frepo/frepo.asc
echo "deb [signed-by=/etc/apt/keyrings/frepo.asc] https://fatumorg.github.io/Frepo/deb trixie-beta main" | sudo tee /etc/apt/sources.list.d/frepo.list
sudo apt update
sudo apt install fatest
```

### Ubuntu

```sh
sudo install -d /etc/apt/keyrings
sudo curl -fsSo /etc/apt/keyrings/frepo.asc https://fatumorg.github.io/Frepo/frepo.asc
echo "deb [signed-by=/etc/apt/keyrings/frepo.asc] https://fatumorg.github.io/Frepo/deb $(. /etc/os-release; echo $VERSION_CODENAME)-beta main" | sudo tee /etc/apt/sources.list.d/frepo.list
sudo apt update
sudo apt install fatest
```

### Fedora

```sh
sudo tee /etc/yum.repos.d/frepo-beta.repo <<'REPO'
[frepo-beta]
name=frepo-beta
baseurl=https://fatumorg.github.io/Frepo/rpm/fedora/$releasever/frepo-beta/x86_64
enabled=1
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://fatumorg.github.io/Frepo/frepo.asc
REPO
sudo dnf install fatest
```

### Void

```sh
sudo mkdir -p /etc/xbps.d
echo "repository=https://fatumorg.github.io/Frepo/void/beta" | sudo tee /etc/xbps.d/frepo.conf
sudo xbps-install -S fatest
```

### Nix

```sh
nix profile install github:fatumorg/Frepo#sylvaris-beta
```

Beta overlays are described under Install, Nix.

## Unavailable

| Package | Target | Reason |
|---|---|---|
| sylvaris, sylstack | Debian 13 | Qt 6.9 required; use Nix |
