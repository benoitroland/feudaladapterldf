Name: ssh-key-retriever
Version: 0.1.0
Release: 1
Summary: Commandline tool for obtaining ssh keys from the bwidm LDAP-Facade
Group: Misc
License: MIT-License
URL: https://git.scc.kit.edu:fum/fum_ldf-interface.git
Source0: ssh-key-retriever.tar

BuildRequires: golang >= 1.7

BuildRoot:	%{_tmppath}/%{name}

%description
Commandline tool for obtaining ssh keys from the bwidm LDAP-Facade

%prep
%setup -q

%build
make 

%install
echo "Buildroot: ${RPM_BUILD_ROOT}"
echo "ENV: "
env | grep -i rpm
echo "PWD"
pwd
make install INSTALL_PATH=${RPM_BUILD_ROOT}/usr MAN_PATH=${RPM_BUILD_ROOT}/usr/share/man CONFIG_PATH=${RPM_BUILD_ROOT}/etc

%files
%defattr(-,root,root,-)
%{_bindir}/*
/etc/ssh-key-retriever.json.conf
/usr/share/doc/ssh-key-retriever/README.md
/usr/share/doc/ssh-key-retriever/Changelog
#%doc
#%{_mandir}/*

%changelog

