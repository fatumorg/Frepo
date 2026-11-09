%global debug_package %{nil}

Name:           tempinfocli
Version:        @pkgver@
Release:        1%{?dist}
Summary:        A live terminal temperature dashboard
License:        MIT
URL:            https://github.com/fatumorg/TempInfoCLI
Source0:        @url@
BuildArch:      noarch
BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros
Requires:       pciutils

%description
A live terminal temperature dashboard.

%prep
%autosetup -n @srcdir@

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files tempinfocli
install -Dpm644 packaging/linux/tempinfo.desktop %{buildroot}%{_datadir}/applications/tempinfo.desktop
install -Dpm644 assets/tempinfo.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/tempinfo.svg
for size in 16 32 48 64 128 256; do
    install -Dpm644 assets/tempinfo-$size.png %{buildroot}%{_datadir}/icons/hicolor/${size}x${size}/apps/tempinfo.png
done

%files -f %{pyproject_files}
%license LICENSE
%{_bindir}/tempinfo
%{_datadir}/applications/tempinfo.desktop
%{_datadir}/icons/hicolor/scalable/apps/tempinfo.svg
%{_datadir}/icons/hicolor/*/apps/tempinfo.png
