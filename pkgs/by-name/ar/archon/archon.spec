%global debug_package %{nil}

Name:           archon
Version:        @pkgver@
Release:        1%{?dist}
Summary:        Linux-native archive browser and mod tool for GTA V
License:        MIT
URL:            https://github.com/fatumorg/archon
Source0:        @url@
BuildRequires:  cmake
BuildRequires:  gcc-c++
BuildRequires:  ninja-build
BuildRequires:  pkgconf-pkg-config
BuildRequires:  qt6-qtbase-devel
BuildRequires:  qt6-qtsvg-devel
BuildRequires:  zlib-devel
BuildRequires:  openssl-devel
BuildRequires:  libzip-devel
BuildRequires:  pugixml-devel
Requires:       qt6-qtsvg

%description
ARCHON browses and edits the archives of GTA V (Legacy and Enhanced) on Linux:
RPF archives, texture dictionaries, models, metadata, OIV packages, ASI plugins
and the Proton prefix, with every change backed up and reversible.

%prep
%autosetup -n @srcdir@

%build
%cmake -G Ninja -DCMAKE_BUILD_TYPE=Release
%cmake_build

%install
%cmake_install

%files
%license LICENSE
%{_bindir}/archon
%{_datadir}/applications/archon.desktop
%{_datadir}/icons/hicolor/scalable/apps/archon.svg
