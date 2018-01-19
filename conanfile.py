#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, AutoToolsBuildEnvironment, RunEnvironment, CMake, tools
import os
import shutil


# this function joins paths together and inverts path separators.
def pjoin(*args, **kwargs):
    return os.path.join(*args, **kwargs).replace(os.path.sep, '/')


class LibcurlConan(ConanFile):
    name = "libcurl"
    version = "7.52.1"
    generators = "cmake", "txt"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False],  # SHARED IN LINUX IS HAVING PROBLEMS WITH LIBEFENCE
               "with_openssl": [True, False],
               "disable_threads": [True, False],
               "with_ldap": [True, False],
               "custom_cacert": [True, False],
               "darwin_ssl": [True, False],
               "with_libssh2": [True, False],
               "with_libidn": [True, False],
               "with_librtmp": [True, False],
               "with_libmetalink": [True, False],
               "with_libpsl": [True, False],
               "with_largemaxwritesize": [True, False],
               "with_nghttp2": [True, False]}
    default_options = ("shared=False", "with_openssl=True", "disable_threads=False",
                       "with_ldap=False", "custom_cacert=False", "darwin_ssl=True",
                       "with_libssh2=False", "with_libidn=False", "with_librtmp=False",
                       "with_libmetalink=False", "with_largemaxwritesize=False",
                       "with_libpsl=False", "with_nghttp2=False")
    exports = ["LICENSE.md"]
    exports_sources = ["FindCURL.cmake", 'patches/*']

    url = "http://github.com/bincrafters/conan-libcurl"
    license = "https://curl.haxx.se/docs/copyright.html"
    website = "https://curl.haxx.se"
    description = "command line tool and library for transferring data with URLs"

    # short_paths = False

    def config_options(self):
        version_components = self.version.split('.')

        del self.settings.compiler.libcxx
        if self.options.with_openssl:
            if self.settings.os != "Macos" or not self.options.darwin_ssl:
                self.options["OpenSSL"].shared = self.options.shared
        if self.options.with_libssh2:
            if self.settings.compiler != "Visual Studio":
                self.options["libssh2"].shared = self.options.shared

        if self.settings.os != "Macos":
            try:
                self.options.remove("darwin_ssl")
            except:
                pass

        # libpsl is supported for libcurl >= 7.46.0
        use_libpsl = int(version_components[0]) == 7 and int(version_components[1]) >= 46
        if not use_libpsl:
            self.options.remove('with_libpsl')

    def build_requirements(self):
        if self.settings.os == "Windows":
            if self.settings.compiler != "Visual Studio":
                self.build_requires("mingw_installer/1.0@conan/stable")
                self.build_requires("msys2_installer/latest@bincrafters/stable")

    def requirements(self):
        if self.options.with_openssl:
            if self.settings.os != "Macos" or not self.options.darwin_ssl:
                self.requires.add("OpenSSL/[>1.0.2a,<1.0.3]@conan/stable", private=False)
            elif self.settings.os == "Macos" and self.options.darwin_ssl:
                self.requires.add("zlib/[~=1.2]@conan/stable", private=False)
        if self.options.with_libssh2:
            if self.settings.compiler != "Visual Studio":
                self.requires.add("libssh2/[~=1.8]@bincrafters/stable", private=False)

        self.requires.add("zlib/[~=1.2]@conan/stable", private=False)

    def configure(self):
        self.is_mingw = self.settings.os == "Windows" and self.settings.compiler == "gcc"

    def source(self):
        tools.get("https://curl.haxx.se/download/curl-%s.tar.gz" % self.version)
        os.rename("curl-%s" % self.version, 'sources')
        tools.download("https://curl.haxx.se/ca/cacert.pem", "cacert.pem", verify=False)
        if self.settings.compiler != "Visual Studio":
            self.run("chmod +x ./sources/configure")

    cfg = {}

    def _add_cfg_option(self, opt_name, var_check=None):
        if not var_check:
            var_check = 'with_%s' % opt_name

        optcheck = getattr(self.options, var_check)
        opt_prefix = 'without' if not optcheck else 'with'
        self.cfg['options'].append("--%s-%s" % (opt_prefix, opt_name))

    def _autotools_config(self):
        version_components = self.version.split('.')

        self.cfg['prefix'] = ['--prefix=%s' % self.package_folder.replace('\\', '/')]

        self.cfg['options'] = []

        use_idn2 = int(version_components[0]) == 7 and int(version_components[1]) >= 53
        if use_idn2:
            self._add_cfg_option('libidn2', 'with_libidn')
        else:
            self._add_cfg_option('libidn')

        self._add_cfg_option('librtmp')
        self._add_cfg_option('libmetalink')

        use_libpsl = int(version_components[0]) == 7 and int(version_components[1]) >= 46
        if use_libpsl:
            self._add_cfg_option('libpsl')

        self._add_cfg_option('nghttp2')

        openssl_path = self.deps_cpp_info["OpenSSL"].rootpath.replace('\\', '/')

        if self.options.with_openssl:
            if self.settings.os == "Macos" and self.options.darwin_ssl:
                self.cfg['options'].append("--with-darwinssl")
            else:
                self.cfg['options'].append("--with-ssl=%s" % openssl_path)
        else:
            self.cfg['options'].append("--without-ssl")

        if self.options.with_libssh2:
            self.cfg['options'].append(
                "--with-libssh2=%s" % self.deps_cpp_info["libssh2"].lib_paths[0].replace('\\', '/'))
        else:
            self.cfg['options'].append("--without-libssh2")

        zlib_path = self.deps_cpp_info["zlib"].rootpath.replace('\\', '/')

        self.cfg['options'].append("--with-zlib=%s" % zlib_path)

        if not self.options.shared:
            self.cfg['options'].append("--disable-shared")
            self.cfg['options'].append("--enable-static")
        else:
            self.cfg['options'].append("--enable-shared")
            self.cfg['options'].append("--disable-static")

        if self.options.disable_threads:
            self.cfg['options'].append("--disable-thread")

        if not self.options.with_ldap:
            self.cfg['options'].append("--disable-ldap")

        if self.options.custom_cacert:
            self.cfg['options'].append("--with-ca-bundle=cacert.pem")

        # for mingw
        if self.is_mingw:
            if self.settings.arch == "x86_64":
                self.cfg['build'] = 'x86_64-w64-mingw32'
                self.cfg['host'] = 'x86_64-w64-mingw32'

            if self.settings.arch == "x86":
                self.cfg['build'] = 'i686-w64-mingw32'
                self.cfg['host'] = 'i686-w64-mingw32'

    def _autotools_bincrafters_build(self):
        version_components = self.version.split('.')

        suffix = ''

        use_idn2 = int(version_components[0]) == 7 and int(version_components[1]) >= 53
        if use_idn2:
            suffix += " --without-libidn2 " if not self.options.with_libidn else " --with-libidn2 "
        else:
            suffix += " --without-libidn " if not self.options.with_libidn else " --with-libidn "
        suffix += " --without-librtmp " if not self.options.with_librtmp else " --with-librtmp "
        suffix += " --without-libmetalink " if not self.options.with_libmetalink else " --with-libmetalink "
        use_libpsl = int(version_components[0]) == 7 and int(version_components[1]) >= 46
        if use_libpsl:
            suffix += " --without-libpsl " if not self.options.with_libpsl else " --with-libpsl "
        suffix += " --without-nghttp2 " if not self.options.with_nghttp2 else " --with-nghttp2 "

        if self.options.with_openssl:
            if self.settings.os == "Macos" and self.options.darwin_ssl:
                suffix += "--with-darwinssl "
            else:
                suffix += "--with-ssl "
        else:
            suffix += "--without-ssl "

        if self.options.with_libssh2:
            suffix += "--with-libssh2=%s " % self.deps_cpp_info["libssh2"].lib_paths[0]
        else:
            suffix += " --without-libssh2 "

        suffix += "--with-zlib=%s " % self.deps_cpp_info["zlib"].lib_paths[0]

        if not self.options.shared:
            suffix += " --disable-shared"

        if self.options.disable_threads:
            suffix += " --disable-thread"

        if not self.options.with_ldap:
            suffix += " --disable-ldap"

        if self.options.custom_cacert:
            suffix += ' --with-ca-bundle=cacert.pem'

        # for mingw
        if self.settings.os == "Windows" and self.settings.compiler == "gcc":
            if self.settings.arch == "x86_64":
                suffix += ' --host=x86_64-w64-mingw32'
            if self.settings.arch == "x86":
                suffix += ' --build=i686-w64-mingw32'
                suffix += ' --host=i686-w64-mingw32'

        env_build = AutoToolsBuildEnvironment(self)

        self.output.warn(repr(env_build.vars))

        with tools.environment_append(env_build.vars):

            env_run = RunEnvironment(self)
            # run configure with *LD_LIBRARY_PATH env vars
            # it allows to pick up shared openssl
            env_run_vars = env_run.vars
            if self.settings.os == "Windows" and self.settings.compiler == "gcc":
                # fix for mingw: RunEnvironment provides backslashes while mingw consumes forward slashes
                for key in env_run_vars.keys():
                    env_run_vars[key] = [tools.unix_path(s) for s in env_run_vars[key]]
            self.output.warn(repr(env_run_vars))
            with tools.environment_append(env_run_vars):

                with tools.chdir(self.name):
                    # disable rpath build
                    tools.replace_in_file("configure", r"-install_name \$rpath/", "-install_name ")

                    # BUG: https://github.com/curl/curl/commit/bd742adb6f13dc668ffadb2e97a40776a86dc124
                    # fixed in 7.54.1: https://github.com/curl/curl/commit/338f427a24f78a717888c7c2b6b91fa831bea28e
                    # so just ignore it if not matched
                    tools.replace_in_file("configure",
                                          'LDFLAGS="`$PKGCONFIG --libs-only-L zlib` $LDFLAGS"',
                                          'LDFLAGS="$LDFLAGS `$PKGCONFIG --libs-only-L zlib`"',
                                          strict=False)

                    cmd = "./configure %s" % suffix
                    self.output.warn(cmd)
                    if self.settings.os == "Windows":
                        tools.run_in_windows_bash(self, cmd)
                    else:
                        self.run(cmd)

                    # temporary fix for xcode9
                    # extremely fragile because make doesn't see CFLAGS from env, only from cmdline
                    if self.settings.os == "Macos":
                        make_suffix = "CFLAGS=\"-Wno-unguarded-availability " + env_build.vars['CFLAGS'] + "\""
                    else:
                        make_suffix = ''

                    cmd = "make %s" % make_suffix
                    self.output.warn(cmd)
                    if self.settings.os == "Windows":
                        tools.run_in_windows_bash(self, cmd)
                    else:
                        self.run(cmd)

    def _autotools_linux(self):
        env_build = AutoToolsBuildEnvironment(self)
        env_build_variables = env_build.vars

        with tools.environment_append(env_build_variables):
            with tools.chdir(self.cfg['src_dir']):
                self.run(pjoin(self.cfg['src_dir'], 'buildconf'))

            tools.mkdir(self.cfg['build_dir'])
            with tools.chdir(self.cfg['build_dir']):
                env_build.configure(configure_dir=self.cfg['src_dir'],
                                    args=self.cfg['prefix'] + self.cfg['options'])

                env_build.make()
                env_build.make(args=['install'])

    def _autotools_mingw(self):
        if self.is_mingw:
            build_cfg = self.cfg['build'] if self.is_mingw else False
            host_cfg = self.cfg['build'] if self.is_mingw else False

            env_build = AutoToolsBuildEnvironment(self, win_bash=self.is_mingw)

            env_build_variables = env_build.vars

            if self.settings.arch == "x86_64":
                env_build.defines.append('_AMD64_')

            env_build_variables['RCFLAGS'] = '-O COFF'
            if self.settings.arch == "x86":
                env_build_variables['RCFLAGS'] += ' --target=pe-i386'
            else:
                env_build_variables['RCFLAGS'] += ' --target=pe-x86-64'

            del env_build_variables['LIBS']

            with tools.environment_append(env_build_variables):

                with tools.chdir(self.cfg['src_dir']):
                    # patch for zlib naming in mingw
                    tools.replace_in_file("configure.ac",
                                          '-lz ',
                                          '-lzlib ',
                                          strict=False)

                    if self.options.shared:
                        # patch for shared mingw build
                        shutil.copy(pjoin(self.build_folder, 'patches', 'lib_Makefile.am.new'),
                                    pjoin(self.cfg['src_dir'], 'lib', 'Makefile.am'))

                    # remove curl.exe build
                    tools.replace_in_file("Makefile.am",
                                          'SUBDIRS = lib src include',
                                          'SUBDIRS = lib include',
                                          strict=True)

                    tools.replace_in_file("Makefile.am",
                                          'include src/Makefile.inc',
                                          '',
                                          strict=True)

                    self.run(pjoin(self.cfg['src_dir'], 'buildconf'), win_bash=self.is_mingw)

                tools.mkdir(self.cfg['build_dir'])
                with tools.chdir(self.cfg['build_dir']):
                    env_build.configure(configure_dir=self.cfg['src_dir'],
                                        args=self.cfg['prefix'] + self.cfg['options'],
                                        build=build_cfg,
                                        host=host_cfg)

                    env_build.make()
                    env_build.make(args=['install'])

                    # no need to distribute docs/man pages
                    shutil.rmtree(os.path.join(self.package_folder, 'share', 'man').replace('\\', '/'))

    def _autotools_conan_build(self):
        self.output.warn(
            '===========================================================================================================')
        self.output.warn("Building with Conan Autotools")

        env_build = AutoToolsBuildEnvironment(self, win_bash=self.is_mingw)

        if self.options.shared:
            if 'LDFLAGS' in os.environ:
                os.environ['LDFLAGS'] = os.environ['LDFLAGS'] + " -shared "
            else:
                os.environ['LDFLAGS'] = " -shared "

        # this has to be specified here or static mingw builds will fail
        if self.is_mingw:
            env_build.libs.append("gdi32")

        if not self.options.shared:
            env_build.defines.append("CURL_STATICLIB=1")

        if self.settings.arch == 'x86_64':
            env_build.defines.append("_AMD64_")

        env_build.defines.append("BUILDING_LIBCURL")

        # else:
        #    env_build.libs.append("curl")

        build_cfg = self.cfg['build'] if self.is_mingw else False
        host_cfg = self.cfg['build'] if self.is_mingw else False

        ###########################################################################################################
        # It is necessary to reorder the paths libraries are searched, becuase zlib is detected in the
        # native mingw environment and used, instead of the one provided by the zlib package
        ###########################################################################################################

        if 'zlib' in env_build.libs: env_build.libs.remove('zlib')

        env_build.library_paths.insert(0, self.deps_cpp_info["zlib"].lib_paths[0].replace('\\', '/'))
        env_build.include_paths.insert(0, self.deps_cpp_info["zlib"].include_paths[0].replace('\\', '/'))
        env_build.libs.insert(0, os.environ['ZLIB_LIBS'])

        env_build_variables = env_build.vars
        self.output.warn(repr(env_build_variables))

        ###########################################################################################################
        # just for debug
        self.output.warn(repr(env_build_variables))

        # env_build.configure(configure_dir='sources',
        #                    args=self.cfg['prefix'] + self.cfg['options'],
        #                    build=build_cfg,
        #                    host=host_cfg)

        # env_build.make()
        # env_build.make(args=['V=1', 'install'])

        with tools.chdir('sources/lib'):
            env_build.make(args=['V=1', '-f', 'Makefile.m32', 'CFG=-zlib-ssl'])
            # env_build.make(args=['V=1', '-f', 'Makefile.m32', 'install'])

        # with tools.environment_append(env_build_variables):

        #    env_run = RunEnvironment(self)
        # run configure with *LD_LIBRARY_PATH env vars
        # it allows to pick up shared openssl
        #    env_run_vars = env_run.vars

        #    with tools.environment_append(env_run_vars):
        # self.output.warn(os.environ['PATH'])
        #        with tools.chdir(self.name):

        #            config_options = self.cfg['prefix'] + ' ' + self.cfg['options']
        #            cmd = "./configure %s" % suffix
        #            self.output.warn(cmd)
        #            if self.settings.os == "Windows":
        #                tools.run_in_windows_bash(self, cmd)
        #            else:
        #                self.run(cmd)

        #            if self.settings.os == "Macos":
        #                make_suffix = "CFLAGS=\"-Wno-unguarded-availability " + env_build.vars['CFLAGS'] + "\""
        #            else:
        #                make_suffix = ''

        #            cmd = "make %s" % make_suffix
        # if self.settings.os == "Windows":
        #    tools.run_in_windows_bash(self, cmd)
        #    #self.run('bash -c "' + cmd + '"')
        # else:
        #            self.run(cmd, win_bash=self.is_mingw)

    def _autotools_bare_build(self):
        # need this for static builds under mingw
        if self.settings.os == "Windows" and self.settings.compiler == "gcc":
            env_build.libs.append("gdi32")

        if not self.options.shared:
            env_build.defines.append("CURL_STATICLIB=1")

        env_build_variables = env_build.vars
        self.output.warn(repr(env_build_variables))

        if self.settings.os == "Windows" and self.settings.compiler == "gcc":
            if 'LDFLAGS' in env_build_variables:
                ldflag_list = env_build_variables['LDFLAGS'].split()
                ldflag_list_tmp = []

                for it in ldflag_list:
                    # self.output.warn("[0]: " + '-L' + self.deps_cpp_info["zlib"].lib_paths[0].replace('\\', '/'))
                    # self.output.warn("[1]: " + it)
                    if it == '-L' + self.deps_cpp_info["zlib"].lib_paths[0].replace('\\', '/'):
                        ldflag_list_tmp.insert(0, it)
                    else:
                        ldflag_list_tmp.append(it)

                env_build_variables['LDFLAGS'] = ' '.join(ldflag_list_tmp)

            if 'CPPFLAGS' in env_build_variables:
                cppflag_list = env_build_variables['CPPFLAGS'].split()
                cppflag_list_tmp = []

                for it in cppflag_list:
                    # self.output.warn("[0]: " + '-L' + self.deps_cpp_info["zlib"].lib_paths[0].replace('\\', '/'))
                    # self.output.warn("[1]: " + it)
                    if it == '-I' + self.deps_cpp_info["zlib"].include_paths[0].replace('\\', '/'):
                        cppflag_list_tmp.insert(0, it)
                    else:
                        cppflag_list_tmp.append(it)

                env_build_variables['CPPFLAGS'] = ' '.join(cppflag_list_tmp)

        self.output.warn(
            '===========================================================================================================')
        self.output.warn(repr(env_build_variables))
        self.output.warn(
            '===========================================================================================================')

        with tools.environment_append(env_build_variables):

            env_run = RunEnvironment(self)
            # run configure with *LD_LIBRARY_PATH env vars
            # it allows to pick up shared openssl
            env_run_vars = env_run.vars

            if self.settings.os == "Windows" and self.settings.compiler == "gcc":
                # fix for mingw: RunEnvironment provides backslashes while mingw consumes forward slashes
                for key in env_run_vars.keys():
                    env_run_vars[key] = [s.replace('\\', '/') for s in env_run_vars[key]]

            self.output.warn(
                '===========================================================================================================')
            self.output.warn(repr(env_run_vars))
            self.output.warn(
                '===========================================================================================================')

            os.environ['AR'] = pjoin(os.environ['MINGW_HOME'], 'bin', 'ar')

            self.output.warn(os.environ['CC'])
            self.output.warn(os.environ['CXX'])
            self.output.warn(os.environ['AR'])

            with tools.environment_append(env_run_vars):

                # self.output.warn(os.environ['PATH'])

                with tools.chdir(self.name):
                    # self.run('bash -c "./buildconf"')
                    # self.run('bash -c "autoreconf -vfi"')

                    # disable rpath build
                    tools.replace_in_file("configure", r"-install_name \$rpath/", "-install_name ")

                    # BUG: https://github.com/curl/curl/commit/bd742adb6f13dc668ffadb2e97a40776a86dc124
                    # fixed in 7.54.1: https://github.com/curl/curl/commit/338f427a24f78a717888c7c2b6b91fa831bea28e
                    # so just ignore it if not matched
                    tools.replace_in_file("configure",
                                          'LDFLAGS="`$PKGCONFIG --libs-only-L zlib` $LDFLAGS"',
                                          'LDFLAGS="$LDFLAGS `$PKGCONFIG --libs-only-L zlib`"',
                                          strict=False)

                    # cmd = "./configure --verbose %s" % suffix
                    # self.output.warn(cmd)
                    # if self.settings.os == "Windows":
                    #    #tools.run_in_windows_bash(self, cmd)
                    #    os.system('bash -c "' + cmd + '"')
                    # else:
                    #    # self.run() freezes on mingw
                    #    os.system(cmd)
                    #    #self.run(cmd)

                    # tools.replace_in_file("Makefile",
                    #                      'ZLIB_LIBS = -lz',
                    #                      'ZLIB_LIBS = -lzlib',
                    #                      strict=False)

                    # temporary fix for xcode9
                    # extremely fragile because make doesn't see CFLAGS from env, only from cmdline
                    if self.settings.os == "Macos":
                        make_suffix = "CFLAGS=\"-Wno-unguarded-availability " + env_build.vars['CFLAGS'] + "\""
                    else:
                        make_suffix = '-j 6 mingw32'
                        make_suffix = ''

                    cmd = "make %s" % make_suffix
                    self.output.warn(cmd)
                    if self.settings.os == "Windows":
                        # tools.run_in_windows_bash(self, cmd)
                        self.run('bash -c "' + cmd + '"')
                    else:
                        self.run(cmd)

    def build(self):
        self.cfg['build_dir'] = pjoin(self.build_folder, 'build')
        self.cfg['src_dir'] = pjoin(self.build_folder, 'sources')

        if self.options.with_largemaxwritesize:
            tools.replace_in_file(pjoin('sources', 'include', 'curl', 'curl.h'),
                                  "define CURL_MAX_WRITE_SIZE 16384",
                                  "define CURL_MAX_WRITE_SIZE 10485760")

        tools.replace_in_file('FindCURL.cmake',
                              'set(CURL_VERSION_STRING "0")',
                              'set(CURL_VERSION_STRING "%s")' % self.version, strict=True)

        use_cmake = self.settings.compiler == "Visual Studio"

        if not use_cmake:
            self._autotools_config()
            if self.is_mingw:
                self._autotools_mingw()

            if self.settings.os == 'Linux':
                self._autotools_linux()
        else:
            # Do not compile curl tool, just library
            conan_magic_lines = '''project(CURL)
cmake_minimum_required(VERSION 3.0)
include(../conanbuildinfo.cmake)
CONAN_BASIC_SETUP()
'''
            cmakelist_file = pjoin('sources', 'CMakeLists.txt')
            tools.replace_in_file(cmakelist_file,
                                  "cmake_minimum_required(VERSION 2.8 FATAL_ERROR)",
                                  conan_magic_lines)

            tools.replace_in_file(cmakelist_file, "project( CURL C )", "")
            tools.replace_in_file(cmakelist_file, "include(CurlSymbolHiding)", "")

            cmakelist_file = pjoin('sources', 'lib', 'CMakeLists.txt')
            # temporary workaround for DEBUG_POSTFIX (curl issues #1796, #2121)
            tools.replace_in_file(cmakelist_file, '  DEBUG_POSTFIX "-d"', '  DEBUG_POSTFIX ""', strict=False)

            cmakelist_file = pjoin('sources', 'src', 'CMakeLists.txt')
            tools.replace_in_file(cmakelist_file, "add_executable(", "IF(0)\n add_executable(")
            tools.replace_in_file(cmakelist_file, "install(TARGETS ${EXE_NAME} DESTINATION bin)", "ENDIF()")  # EOF

            # tools.mkdir(os.path.join(self.name, '_build'))

            cmake = CMake(self)
            cmake.definitions['BUILD_TESTING'] = False
            cmake.definitions['CURL_DISABLE_LDAP'] = not self.options.with_ldap
            cmake.definitions['BUILD_SHARED_LIBS'] = self.options.shared
            cmake.definitions['CURL_STATICLIB'] = not self.options.shared
            cmake.definitions['CMAKE_DEBUG_POSTFIX'] = ''
            cmake.configure(source_dir=self.cfg['src_dir'], build_dir=self.cfg['build_dir'])
            cmake.build()
            cmake.install()

    def package(self):
        self.copy("COPYING", src="sources", dst="licenses", ignore_case=True, keep_path=False)

        # Copy findZLIB.cmake to package
        self.copy("FindCURL.cmake", ".", ".")

        # Copying zlib.h, zutil.h, zconf.h
        # self.copy("*.h", "include/curl", "%s" % self.name, keep_path=True)

        # Copy the certs to be used by client
        self.copy(pattern="cacert.pem", keep_path=False)

        # Copying static and dynamic libs
        if self.settings.compiler != "Visual Studio":
            if self.settings.os == "Windows":
                if self.options.shared:
                    self.copy(pattern="*.dll", dst="bin", src='build/lib', keep_path=False)
                    self.copy(pattern="*dll.a", dst="lib", src='build/lib', keep_path=False)
                    self.copy(pattern="*.def", dst="lib", src='build/lib', keep_path=False)
                    self.copy(pattern="*.lib", dst="lib", src='build/lib', keep_path=False)
            else:
                if self.options.shared:
                    if self.settings.os == "Macos":
                        self.copy(pattern="*.dylib", dst="lib", keep_path=False, links=True)
                    else:
                        self.copy(pattern="*.so*", dst="lib", src=self.name, keep_path=False, links=True)
                else:
                    self.copy(pattern="*.a", dst="lib", src=self.name, keep_path=False, links=True)

    def package_info(self):
        if self.settings.compiler != "Visual Studio":
            self.cpp_info.libs = ['curl']

            if self.settings.os == "Linux":
                self.cpp_info.libs.extend(["rt", "pthread"])
                if self.options.with_libssh2:
                    self.cpp_info.libs.extend(["ssh2"])
                if self.options.with_libidn:
                    self.cpp_info.libs.extend(["idn"])
                if self.options.with_librtmp:
                    self.cpp_info.libs.extend(["rtmp"])
            if self.settings.os == "Macos":
                if self.options.with_ldap:
                    self.cpp_info.libs.extend(["ldap"])
                if self.options.darwin_ssl:
                    # self.cpp_info.libs.extend(["/System/Library/Frameworks/Cocoa.framework", "/System/Library/Frameworks/Security.framework"])
                    self.cpp_info.exelinkflags.append("-framework Cocoa")
                    self.cpp_info.exelinkflags.append("-framework Security")
                    self.cpp_info.sharedlinkflags = self.cpp_info.exelinkflags
        else:
            self.cpp_info.libs = ['libcurl_imp'] if self.options.shared else ['libcurl']
            self.cpp_info.libs.append('Ws2_32')
            if self.options.with_ldap:
                self.cpp_info.libs.append("wldap32")
            if self.options.with_openssl:
                self.cpp_info.libs.extend(self.deps_cpp_info['OpenSSL'].libs)

        if not self.options.shared:
            self.cpp_info.defines.append("CURL_STATICLIB=1")
