{ pkgs, frepo }:

import "${frepo.src}/default.nix" { inherit pkgs; }
