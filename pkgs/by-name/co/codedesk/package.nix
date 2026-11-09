{ lib, rustPlatform, makeDesktopItem, pkg-config, wrapGAppsHook3, webkitgtk_4_1, gtk3, libsoup_3, glib-networking, openssl, libxkbcommon, libxcb, xorg, wayland, dbus, pipewire, libgbm, libdrm, frepo }:

let
  desktop = makeDesktopItem {
    name = "codedesk";
    desktopName = "Codedesk";
    exec = "codedesk %U";
    icon = "codedesk";
    categories = [ "Development" ];
    startupWMClass = "codedesk";
    comment = "Desktop workspace for Claude Code";
  };
in
rustPlatform.buildRustPackage {
  pname = "codedesk";
  inherit (frepo) version src;
  cargoLock.lockFile = "${frepo.src}/Cargo.lock";
  nativeBuildInputs = [ pkg-config wrapGAppsHook3 rustPlatform.bindgenHook ];
  buildInputs = [ webkitgtk_4_1 gtk3 libsoup_3 glib-networking openssl libxkbcommon libxcb xorg.libX11 xorg.libXtst xorg.libXi xorg.libXrandr wayland dbus pipewire libgbm libdrm ];
  doCheck = false;
  postInstall = ''
    install -Dm644 ${desktop}/share/applications/codedesk.desktop $out/share/applications/codedesk.desktop
    install -Dm644 ui/icons/icon.svg $out/share/icons/hicolor/scalable/apps/codedesk.svg
    install -Dm644 ui/icons/icon.png $out/share/icons/hicolor/512x512/apps/codedesk.png
  '';
  meta = {
    mainProgram = "codedesk";
  };
}
