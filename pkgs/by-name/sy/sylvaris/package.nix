{ callPackage, sylstack, frepo }:

callPackage "${frepo.src}/nix/package.nix" { inherit sylstack; commit = frepo.tag; }
