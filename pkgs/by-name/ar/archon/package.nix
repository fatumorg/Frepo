{ lib, stdenv, cmake, ninja, pkg-config, qt6, zlib, openssl, libzip, pugixml, protontricks, frepo }:

stdenv.mkDerivation {
  pname = "archon";
  inherit (frepo) version src;
  nativeBuildInputs = [ cmake ninja pkg-config qt6.wrapQtAppsHook ];
  buildInputs = [ qt6.qtbase qt6.qtsvg zlib openssl libzip pugixml ];
  qtWrapperArgs = [ "--suffix PATH : ${lib.makeBinPath [ protontricks ]}" ];
  doCheck = false;
  meta = {
    description = "Linux-native archive browser and mod tool for GTA V";
    homepage = "https://github.com/fatumorg/archon";
    license = lib.licenses.mit;
    mainProgram = "archon";
  };
}
