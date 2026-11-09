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

## Install

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

## Unavailable
