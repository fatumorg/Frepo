%global debug_package %{nil}

Name:           sylvaris
Version:        @pkgver@
Release:        1%{?dist}
Summary:        Modular desktop shell for Hyprland, niri and sway, built on SylStack
License:        MIT
URL:            https://github.com/fatumorg/Sylvaris
Source0:        @url@
BuildArch:      noarch
Requires:       sylstack
Requires:       qt6-qtdeclarative
Requires:       qt6-qtwayland
Requires:       qt6-qtsvg
Requires:       qt6-qtmultimedia
Requires:       qt6-qtimageformats
Requires:       layer-shell-qt
Requires:       polkit-qt6-1
Requires:       kf6-syntax-highlighting
Requires:       rsms-inter-fonts
Requires:       jetbrains-mono-fonts
Requires:       bash
Requires:       coreutils
Requires:       procps-ng
Requires:       util-linux
Recommends:     ibm-plex-mono-fonts
Recommends:     pipewire-utils
Recommends:     pulseaudio-utils
Recommends:     python3
Recommends:     python3-cryptography
Recommends:     python3-gobject
Recommends:     libnotify
Recommends:     NetworkManager
Recommends:     wlr-randr
Recommends:     wayvnc
Recommends:     openssl
Recommends:     iproute
Recommends:     brightnessctl
Recommends:     ddcutil
Recommends:     wlsunset
Recommends:     curl
Recommends:     wl-clipboard
Recommends:     grim
Recommends:     slurp
Recommends:     wf-recorder
Recommends:     ffmpeg-free
Recommends:     bsdtar
Recommends:     bsdcat
Recommends:     wtype
Recommends:     glib2
Recommends:     git
Recommends:     cava
Recommends:     udisks2

%description
Modular desktop shell for Hyprland, niri and sway, built on SylStack.

%prep
%autosetup -n @srcdir@

%install
install -Dpm755 bin/sylvaris %{buildroot}%{_bindir}/sylvaris
install -d %{buildroot}%{_datadir}/sylvaris
cp -r shell/. %{buildroot}%{_datadir}/sylvaris/
printf '%%s\n' %{version} > %{buildroot}%{_datadir}/sylvaris/COMMIT
install -Dpm644 -t %{buildroot}%{_datadir}/applications share/applications/*.desktop
install -Dpm644 -t %{buildroot}%{_datadir}/icons/hicolor/scalable/apps share/icons/hicolor/scalable/apps/*.svg
install -Dpm644 dist/pam/sylvaris %{buildroot}%{_sysconfdir}/pam.d/sylvaris

%files
%license LICENSE
%{_bindir}/sylvaris
%{_datadir}/sylvaris
%{_datadir}/applications/sylvaris*.desktop
%{_datadir}/icons/hicolor/scalable/apps/sylvaris-*.svg
%config(noreplace) %{_sysconfdir}/pam.d/sylvaris
