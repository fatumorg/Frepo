{
  description = "naxce's packages for every Linux distro";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }: {
    packages.x86_64-linux = { };
    checks.x86_64-linux = { };
  };
}
