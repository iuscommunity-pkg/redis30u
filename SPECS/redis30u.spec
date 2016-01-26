%global real_name redis
%global ius_suffix 30u
%global _hardened_build 1
%global with_perftools 0

%if 0%{?fedora} >= 19 || 0%{?rhel} >= 7
%global with_systemd 1
%global with_procps_ng 1
%else
%global with_systemd 0
%global with_procps_ng 0
%endif

%global with_tests 1

Name:              %{real_name}%{ius_suffix}
Version:           3.0.7
Release:           1.ius%{?dist}
Summary:           A persistent key-value database
%if 0%{?rhel} <= 6
Group:             Applications/Databases
%endif
License:           BSD
URL:               http://redis.io

Source0:           http://download.redis.io/releases/%{real_name}-%{version}.tar.gz
Source1:           %{real_name}.logrotate
Source2:           %{real_name}-sentinel.service
Source3:           %{real_name}.service
Source4:           %{real_name}.tmpfiles
Source5:           %{real_name}-sentinel.init
Source6:           %{real_name}.init
Source7:           %{real_name}-shutdown
Source8:           %{real_name}-limit-systemd
Source9:           %{real_name}-limit-init

# To refresh patches:
# tar xf redis-xxx.tar.gz && cd redis-xxx && git init && git add . && git commit -m "%{version} baseline"
# git am %{patches}
# Then refresh your patches
# git format-patch HEAD~<number of expected patches>
# Update configuration for Fedora
Patch0001:            0001-redis-2.8.18-redis-conf.patch
Patch0002:            0002-redis-2.8.18-deps-library-fPIC-performance-tuning.patch
Patch0003:            0003-redis-2.8.18-use-system-jemalloc.patch
# tests/integration/replication-psync.tcl failed on slow machines(GITHUB #1417)
Patch0004:            0004-redis-2.8.18-disable-test-failed-on-slow-machine.patch
# Fix sentinel configuration to use a different log file than redis
Patch0005:            0005-redis-2.8.18-sentinel-configuration-file-fix.patch

%if 0%{?with_perftools}
BuildRequires:     gperftools-devel
%else
BuildRequires:     jemalloc-devel
%endif # with_perftools

%if 0%{?with_tests}
BuildRequires:     tcl
%if 0%{?with_procps_ng}
BuildRequires:     procps-ng
%else
BuildRequires:     procps
%endif # with_procps_ng
%endif # with_tests

%if 0%{?with_systemd}
BuildRequires:     systemd
%endif # with_systemd

# Required for redis-shutdown
Requires:          /bin/awk
Requires:          logrotate
Requires(pre):     shadow-utils

%if 0%{?with_systemd}
Requires(post):    systemd
Requires(preun):   systemd
Requires(postun):  systemd
%else
Requires(post):    chkconfig
Requires(preun):   chkconfig
Requires(preun):   initscripts
Requires(postun):  initscripts
%endif # with_systemd

Provides: %{real_name} = %{version}-%{release}
Provides: %{real_name}%{?_isa} = %{version}-%{release}
Provides: config(%{real_name}) = %{version}-%{release}
Conflicts: %{real_name} < %{version}


%description
Redis is an advanced key-value store. It is often referred to as a data 
structure server since keys can contain strings, hashes, lists, sets and 
sorted sets.

You can run atomic operations on these types, like appending to a string;
incrementing the value in a hash; pushing to a list; computing set 
intersection, union and difference; or getting the member with highest 
ranking in a sorted set.

In order to achieve its outstanding performance, Redis works with an 
in-memory dataset. Depending on your use case, you can persist it either 
by dumping the dataset to disk every once in a while, or by appending 
each command to a log.

Redis also supports trivial-to-setup master-slave replication, with very 
fast non-blocking first synchronization, auto-reconnection on net split 
and so forth.

Other features include Transactions, Pub/Sub, Lua scripting, Keys with a 
limited time-to-live, and configuration settings to make Redis behave like 
a cache.

You can use Redis from most programming languages also.


%prep
%setup -q -n %{real_name}-%{version}
rm -frv deps/jemalloc
%patch0001 -p1
%patch0002 -p1
%patch0003 -p1
%patch0004 -p1
%patch0005 -p1

# No hidden build.
sed -i -e 's|\t@|\t|g' deps/lua/src/Makefile
sed -i -e 's|$(QUIET_CC)||g' src/Makefile
sed -i -e 's|$(QUIET_LINK)||g' src/Makefile
sed -i -e 's|$(QUIET_INSTALL)||g' src/Makefile
# Ensure deps are built with proper flags
sed -i -e 's|$(CFLAGS)|%{optflags}|g' deps/Makefile
sed -i -e 's|OPTIMIZATION?=-O3|OPTIMIZATION=%{optflags}|g' deps/hiredis/Makefile
sed -i -e 's|$(LDFLAGS)|%{?__global_ldflags}|g' deps/hiredis/Makefile
sed -i -e 's|$(CFLAGS)|%{optflags}|g' deps/linenoise/Makefile
sed -i -e 's|$(LDFLAGS)|%{?__global_ldflags}|g' deps/linenoise/Makefile


%build
make %{?_smp_mflags} \
    DEBUG="" \
    LDFLAGS="%{?__global_ldflags}" \
    CFLAGS+="%{optflags}" \
    LUA_LDFLAGS+="%{?__global_ldflags}" \
%if 0%{?with_perftools}
    MALLOC=tcmalloc \
%else
    MALLOC=jemalloc \
%endif # with_perftools
    all


%install
make install INSTALL="install -p" PREFIX=%{buildroot}%{_prefix}

# Filesystem.
install -d %{buildroot}%{_sharedstatedir}/%{real_name}
install -d %{buildroot}%{_localstatedir}/log/%{real_name}
install -d %{buildroot}%{_localstatedir}/run/%{real_name}

# Install logrotate file.
install -pDm644 %{S:1} %{buildroot}%{_sysconfdir}/logrotate.d/%{real_name}

# Install configuration files.
install -pDm644 %{real_name}.conf %{buildroot}%{_sysconfdir}/%{real_name}.conf
install -pDm644 sentinel.conf %{buildroot}%{_sysconfdir}/%{real_name}-sentinel.conf

%if 0%{?with_systemd}
# Install Systemd unit files.
mkdir -p %{buildroot}%{_unitdir}
install -pm644 %{S:3} %{buildroot}%{_unitdir}
install -pm644 %{S:2} %{buildroot}%{_unitdir}
# Install systemd tmpfiles config.
install -pDm644 %{S:4} %{buildroot}%{_tmpfilesdir}/%{real_name}.conf
# Install systemd limit files (requires systemd >= 204)
install -pDm644 %{S:8} %{buildroot}%{_sysconfdir}/systemd/system/%{real_name}.service.d/limit.conf
install -pDm644 %{S:8} %{buildroot}%{_sysconfdir}/systemd/system/%{real_name}-sentinel.service.d/limit.conf
%else
# Install SysV service files.
install -pDm755 %{S:5} %{buildroot}%{_initrddir}/%{real_name}-sentinel
install -pDm755 %{S:6} %{buildroot}%{_initrddir}/%{real_name}
install -pDm644 %{S:9} %{buildroot}%{_sysconfdir}/security/limits.d/95-%{real_name}.conf
%endif # with_systemd

# Fix non-standard-executable-perm error.
chmod 755 %{buildroot}%{_bindir}/%{real_name}-*

# create redis-sentinel command as described on
# http://redis.io/topics/sentinel
ln -sf %{real_name}-server %{buildroot}%{_bindir}/%{real_name}-sentinel

# Install redis-shutdown
install -pDm755 %{S:7} %{buildroot}%{_bindir}/%{real_name}-shutdown


%check
%if 0%{?with_tests}
make test
make test-sentinel
%endif # with_tests


%pre
getent group %{real_name} &> /dev/null || \
groupadd -r %{real_name} &> /dev/null
getent passwd %{real_name} &> /dev/null || \
useradd -r -g %{real_name} -d %{_sharedstatedir}/%{real_name} -s /sbin/nologin \
-c 'Redis Database Server' %{real_name} &> /dev/null
exit 0


%post
%if 0%{?with_systemd}
%systemd_post %{real_name}.service
%systemd_post %{real_name}-sentinel.service
%else
chkconfig --add %{real_name}
chkconfig --add %{real_name}-sentinel
%endif # with_systemd


%preun
%if 0%{?with_systemd}
%systemd_preun %{real_name}.service
%systemd_preun %{real_name}-sentinel.service
%else
if [ $1 -eq 0 ] ; then
    service %{real_name} stop &> /dev/null
    chkconfig --del %{real_name} &> /dev/null
    service %{real_name}-sentinel stop &> /dev/null
    chkconfig --del %{real_name}-sentinel &> /dev/null
fi
%endif # with_systemd


%postun
%if 0%{?with_systemd}
%systemd_postun_with_restart %{real_name}.service
%systemd_postun_with_restart %{real_name}-sentinel.service
%else
if [ "$1" -ge "1" ] ; then
    service %{real_name} condrestart >/dev/null 2>&1 || :
    service %{real_name}-sentinel condrestart >/dev/null 2>&1 || :
fi
%endif # with_systemd


%files
%{!?_licensedir:%global license %%doc}
%license COPYING
%doc 00-RELEASENOTES BUGS CONTRIBUTING MANIFESTO README
%config(noreplace) %{_sysconfdir}/logrotate.d/%{real_name}
%attr(0644, redis, root) %config(noreplace) %{_sysconfdir}/%{real_name}.conf
%attr(0644, redis, root) %config(noreplace) %{_sysconfdir}/%{real_name}-sentinel.conf
%dir %attr(0755, redis, redis) %{_sharedstatedir}/%{real_name}
%dir %attr(0755, redis, redis) %{_localstatedir}/log/%{real_name}
%dir %attr(0755, redis, redis) %{_localstatedir}/run/%{real_name}
%{_bindir}/%{real_name}-*
%if 0%{?with_systemd}
%{_tmpfilesdir}/%{real_name}.conf
%{_unitdir}/%{real_name}.service
%{_unitdir}/%{real_name}-sentinel.service
%dir %{_sysconfdir}/systemd/system/%{real_name}.service.d
%config(noreplace) %{_sysconfdir}/systemd/system/%{real_name}.service.d/limit.conf
%dir %{_sysconfdir}/systemd/system/%{real_name}-sentinel.service.d
%config(noreplace) %{_sysconfdir}/systemd/system/%{real_name}-sentinel.service.d/limit.conf
%else
%{_initrddir}/%{real_name}
%{_initrddir}/%{real_name}-sentinel
%config(noreplace) %{_sysconfdir}/security/limits.d/95-%{real_name}.conf
%endif # with_systemd


%changelog
* Tue Jan 26 2016 Ben Harper <ben.harper@rackspace.com> - 3.0.7-1.ius
- Latest upstream

* Mon Dec 21 2015 Carl George <carl.george@rackspace.com> - 3.0.6-1.ius
- Latest upstream

* Fri Oct 16 2015 Carl George <carl.george@rackspace.com> - 3.0.5-1.ius
- Latest upstream

* Tue Sep 08 2015 Carl George <carl.george@rackspace.com> - 3.0.4-1.ius
- Latest upstream

* Fri Jul 17 2015 Carl George <carl.george@rackspace.com> - 3.0.3-1.ius
- Latest upstream

* Thu Jun 04 2015 Ben Harper <ben.harper@rackspace.com> - 3.0.2-1.ius
- Latest upstream

* Tue May 05 2015 Carl George <carl.george@rackspace.com> - 3.0.1-1.ius
- Latest upstream

* Fri Apr 10 2015 Carl George <carl.george@rackspace.com> - 3.0.0-1.ius
- Port from Fedora to IUS
- Use procps-ng on EL7 only
- Enforce test suite
- Ensure sentinel log gets rotated (Remi Collet)

* Thu Apr  2 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 3.0.0-1
- Upstream 3.0.0 (RHBZ #1208322)

* Thu Mar 26 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.19-2
- Fix redis-shutdown on multiple NIC setup (RHBZ #1201237)

* Fri Feb 27 2015 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.19-1
- Upstream 2.8.19 (RHBZ #1175232)
- Fix permissions for tmpfiles (RHBZ #1182913)
- Add limits config files
- Spec cleanups

* Fri Dec 05 2014 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.18-1
- Upstream 2.8.18
- Rebased patches

* Sat Sep 20 2014 Remi Collet <remi@fedoraproject.org> - 2.8.17-1
- Upstream 2.8.17
- fix redis-sentinel service unit file for systemd
- fix redis-shutdown for sentinel
- also use redis-shutdown in init scripts

* Wed Sep 17 2014 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.15-2
- Minor fix to redis-shutdown (from Remi Collet)

* Sat Sep 13 2014 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.15-1
- Upstream 2.8.15 (critical bugfix for sentinel)
- Fix to sentinel systemd service and configuration (thanks Remi)
- Refresh patch management

* Thu Sep 11 2014 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.14-2
- Cleanup spec
- Fix shutdown for redis-{server,sentinel}
- Backport fixes from Remi Collet repository (ie: sentinel working)

* Thu Sep 11 2014 Haïkel Guémar <hguemar@fedoraproject.org> - 2.8.14-1
- Upstream 2.8.14 (RHBZ #1136287)
- Bugfix for lua scripting users (server crash)
- Refresh patches
- backport spec from EPEL7 (thanks Warren)

* Wed Jul 16 2014 Christopher Meng <rpm@cicku.me> - 2.8.13-1
- Update to 2.8.13

* Tue Jun 24 2014 Christopher Meng <rpm@cicku.me> - 2.8.12-1
- Update to 2.8.12

* Wed Jun 18 2014 Christopher Meng <rpm@cicku.me> - 2.8.11-1
- Update to 2.8.11

* Sun Jun 08 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.6.16-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Fri Sep 06 2013 Fabian Deutsch <fabian.deutsch@gmx.de> - 2.6.16-1
- Update to 2.6.16
- Fix rhbz#973151
- Fix rhbz#656683
- Fix rhbz#977357 (Jan Vcelak <jvcelak@fedoraproject.org>)

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.6.13-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Tue Jul 23 2013 Peter Robinson <pbrobinson@fedoraproject.org> 2.6.13-4
- ARM has gperftools

* Wed Jun 19 2013 Fabian Deutsch <fabiand@fedoraproject.org> - 2.6.13-3
- Modify jemalloc patch for s390 compatibility (Thanks sharkcz)

* Fri Jun 07 2013 Fabian Deutsch <fabiand@fedoraproject.org> - 2.6.13-2
- Unbundle jemalloc

* Fri Jun 07 2013 Fabian Deutsch <fabiand@fedoraproject.org> - 2.6.13-1
- Add compile PIE flag (rhbz#955459)
- Update to redis 2.6.13 (rhbz#820919)

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.6.7-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Thu Dec 27 2012 Silas Sewell <silas@sewell.org> - 2.6.7-1
- Update to redis 2.6.7

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.4.15-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Sun Jul 08 2012 Silas Sewell <silas@sewell.org> - 2.4.15-2
- Remove TODO from docs

* Sun Jul 08 2012 Silas Sewell <silas@sewell.org> - 2.4.15-1
- Update to redis 2.4.15

* Sat May 19 2012 Silas Sewell <silas@sewell.org> - 2.4.13-1
- Update to redis 2.4.13

* Sat Mar 31 2012 Silas Sewell <silas@sewell.org> - 2.4.10-1
- Update to redis 2.4.10

* Fri Feb 24 2012 Silas Sewell <silas@sewell.org> - 2.4.8-1
- Update to redis 2.4.8

* Sat Feb 04 2012 Silas Sewell <silas@sewell.org> - 2.4.7-1
- Update to redis 2.4.7

* Wed Feb 01 2012 Fabian Deutsch <fabiand@fedoraproject.org> - 2.4.6-4
- Fixed a typo in the spec

* Tue Jan 31 2012 Fabian Deutsch <fabiand@fedoraproject.org> - 2.4.6-3
- Fix .service file, to match config (Type=simple).

* Tue Jan 31 2012 Fabian Deutsch <fabiand@fedoraproject.org> - 2.4.6-2
- Fix .service file, credits go to Timon.

* Thu Jan 12 2012 Fabian Deutsch <fabiand@fedoraproject.org> - 2.4.6-1
- Update to 2.4.6
- systemd unit file added
- Compiler flags changed to compile 2.4.6
- Remove doc/ and Changelog

* Sun Jul 24 2011 Silas Sewell <silas@sewell.org> - 2.2.12-1
- Update to redis 2.2.12

* Fri May 06 2011 Dan Horák <dan[at]danny.cz> - 2.2.5-2
- google-perftools exists only on selected architectures

* Sat Apr 23 2011 Silas Sewell <silas@sewell.ch> - 2.2.5-1
- Update to redis 2.2.5

* Sat Mar 26 2011 Silas Sewell <silas@sewell.ch> - 2.2.2-1
- Update to redis 2.2.2

* Wed Feb 09 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.0.4-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Sun Dec 19 2010 Silas Sewell <silas@sewell.ch> - 2.0.4-1
- Update to redis 2.0.4

* Tue Oct 19 2010 Silas Sewell <silas@sewell.ch> - 2.0.3-1
- Update to redis 2.0.3

* Fri Oct 08 2010 Silas Sewell <silas@sewell.ch> - 2.0.2-1
- Update to redis 2.0.2
- Disable checks section for el5

* Sat Sep 11 2010 Silas Sewell <silas@sewell.ch> - 2.0.1-1
- Update to redis 2.0.1

* Sat Sep 04 2010 Silas Sewell <silas@sewell.ch> - 2.0.0-1
- Update to redis 2.0.0

* Thu Sep 02 2010 Silas Sewell <silas@sewell.ch> - 1.2.6-3
- Add Fedora build flags
- Send all scriplet output to /dev/null
- Remove debugging flags
- Add redis.conf check to init script

* Mon Aug 16 2010 Silas Sewell <silas@sewell.ch> - 1.2.6-2
- Don't compress man pages
- Use patch to fix redis.conf

* Tue Jul 06 2010 Silas Sewell <silas@sewell.ch> - 1.2.6-1
- Initial package
