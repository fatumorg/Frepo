%global debug_package %{nil}
%global __strip /bin/true

Name:           codedesk
Version:        @pkgver@
Release:        1%{?dist}
Summary:        Codedesk: a desktop workspace for Claude Code
License:        MIT
URL:            https://github.com/fatumorg/codedesk
Source0:        @url@
BuildRequires:  cargo
BuildRequires:  rust
BuildRequires:  gcc
BuildRequires:  clang-devel
BuildRequires:  pkgconf-pkg-config
BuildRequires:  webkit2gtk4.1-devel
BuildRequires:  gtk3-devel
BuildRequires:  libsoup3-devel
BuildRequires:  openssl-devel
BuildRequires:  libxkbcommon-devel
BuildRequires:  libxcb-devel
BuildRequires:  libX11-devel
BuildRequires:  libXtst-devel
BuildRequires:  libXi-devel
BuildRequires:  libXrandr-devel
BuildRequires:  wayland-devel
BuildRequires:  dbus-devel
BuildRequires:  pipewire-devel
BuildRequires:  mesa-libgbm-devel
BuildRequires:  libdrm-devel
Requires:       glib-networking

%description
Codedesk: a desktop workspace for Claude Code.

%prep
%autosetup -n @srcdir@

%build
cargo build --release --locked

%install
install -Dpm755 target/release/codedesk %{buildroot}%{_bindir}/codedesk
install -Dpm644 ui/icons/icon.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/codedesk.svg
install -Dpm644 ui/icons/icon.png %{buildroot}%{_datadir}/icons/hicolor/512x512/apps/codedesk.png
install -d %{buildroot}%{_datadir}/applications
printf '%s\n' '[Desktop Entry]' 'Type=Application' 'Name=Codedesk' 'Exec=codedesk %%U' 'Icon=codedesk' 'Categories=Development;' 'StartupWMClass=codedesk' 'Comment=Desktop workspace for Claude Code' > %{buildroot}%{_datadir}/applications/codedesk.desktop

%files
%{_bindir}/codedesk
%{_datadir}/applications/codedesk.desktop
%{_datadir}/icons/hicolor/scalable/apps/codedesk.svg
%{_datadir}/icons/hicolor/512x512/apps/codedesk.png
