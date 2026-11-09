{
  description = "naxce's packages for every Linux distro";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      lib = nixpkgs.lib;
      pkgs = nixpkgs.legacyPackages.${system};
      root = ./pkgs/by-name;

      metas = lib.listToAttrs (lib.concatLists (lib.mapAttrsToList
        (shard: _: lib.mapAttrsToList
          (name: _: lib.nameValuePair name (builtins.fromJSON (builtins.readFile (root + "/${shard}/${name}/version.json"))))
          (builtins.readDir (root + "/${shard}")))
        (builtins.readDir root)));

      shardOf = name: builtins.substring 0 2 name;

      fetch = meta: entry: builtins.fetchTree {
        type = "tarball";
        url = "https://github.com/${meta.repo}/archive/refs/tags/${entry.tag}.tar.gz";
        narHash = entry.hash;
      };

      resolve = channel: meta:
        if channel == "beta" && meta.beta != null then meta.beta else meta.stable;

      channelSet = pkgs: channel:
        let
          entries = lib.filterAttrs (_: e: e != null) (lib.mapAttrs (_: resolve channel) metas);
          scope = lib.makeScope pkgs.newScope (s: lib.mapAttrs
            (name: entry: s.callPackage (root + "/${shardOf name}/${name}/package.nix") {
              frepo = {
                src = fetch metas.${name} entry;
                inherit (entry) tag version;
              };
            })
            entries);
        in
        lib.getAttrs (builtins.attrNames entries) scope;

      stable = channelSet pkgs "stable";
      betaSet = channelSet pkgs "beta";
      all = stable // lib.mapAttrs' (n: v: lib.nameValuePair "${n}-beta" v) betaSet;

      sylvarisSrc = fetch metas.sylvaris metas.sylvaris.stable;
    in {
      packages.${system} = all;
      checks.${system} = all;

      overlays = {
        default = final: _: channelSet final "stable";
        beta = final: _: channelSet final "beta";
      };

      nixosModules = rec {
        sylvaris = import "${sylvarisSrc}/nix/nixos-module.nix" { packages = self.packages; };
        default = sylvaris;
      };

      homeManagerModules = rec {
        sylvaris = import "${sylvarisSrc}/nix/hm-module.nix" { packages = self.packages; };
        default = sylvaris;
      };
    };
}
