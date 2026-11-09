%global debug_package %{nil}

Name:           fatest
Version:        @pkgver@
Release:        1%{?dist}
Summary:        A fast, clean terminal speedtest tool
License:        MIT
URL:            https://github.com/naxce/fatest
Source0:        @url@
BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros

%description
A fast, clean terminal speedtest tool.

%prep
%autosetup -n @srcdir@

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files fatest
install -Dpm644 packaging/linux/fatest.desktop %{buildroot}%{_datadir}/applications/fatest.desktop
install -Dpm644 assets/fatest-256.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/fatest.png

%files -f %{pyproject_files}
%license LICENSE
%{_bindir}/fatest
%{_datadir}/applications/fatest.desktop
%{_datadir}/icons/hicolor/256x256/apps/fatest.png
