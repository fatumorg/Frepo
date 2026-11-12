{ callPackage, sylstack, frepo, sylvarisParts ? { } }:

callPackage "${frepo.src}/nix/package.nix" { inherit sylstack sylvarisParts; commit = frepo.tag; }
