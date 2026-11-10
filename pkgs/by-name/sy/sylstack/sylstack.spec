%global debug_package %{nil}
%global _vpath_srcdir stack

Name:           sylstack
Version:        @pkgver@
Release:        1%{?dist}
Summary:        Small Qt Quick runtime for Wayland desktop shells, made for Sylvaris
License:        MIT
URL:            https://github.com/fatumorg/Sylvaris
Source0:        @url@
BuildRequires:  cmake
BuildRequires:  gcc-c++
BuildRequires:  ninja-build
BuildRequires:  pkgconf-pkg-config
BuildRequires:  qt6-qtbase-devel
BuildRequires:  qt6-qtbase-private-devel
BuildRequires:  qt6-qtdeclarative-devel
BuildRequires:  qt6-qtsvg-devel
BuildRequires:  qt6-qtwayland-devel
BuildRequires:  layer-shell-qt-devel
BuildRequires:  polkit-qt6-1-devel
BuildRequires:  pipewire-devel
BuildRequires:  pam-devel
BuildRequires:  wayland-devel
Requires:       qt6-qtdeclarative
Requires:       qt6-qtwayland
Requires:       qt6-qtsvg
Requires:       layer-shell-qt

%description
Small Qt Quick runtime for Wayland desktop shells, made for Sylvaris.

%prep
%autosetup -n @srcdir@

%build
%cmake -G Ninja -DCMAKE_BUILD_TYPE=Release
%cmake_build

%install
%cmake_install

%files
%license LICENSE
%{_bindir}/sylstack
%{_libdir}/qt-6/qml/SylStack
