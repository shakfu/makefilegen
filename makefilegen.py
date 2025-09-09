#!/usr/bin/env python3
"""makefilegen: makefile generator

Makefile generator / direct compilation tool,
extracted from my work in shedskin.makefile in the shedskin project,
as this generic part of the code may be generally useful.
https://github.com/shedskin/shedskin
"""

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path
from typing import Any, Callable, Optional, TypeAlias


# type aliases
PathLike: TypeAlias = Path | str
TestFunc: TypeAlias = Callable[[str], bool]

# constants
PLATFORM = platform.system()

VERSION = float(
    subprocess.check_output(["make", "-v"])
    .decode()
    .split("\n")[0]
    .replace("GNU Make ", "")
)


# -----------------------------------------------------------------------------
# utility functions]


def always_true(_: Any) -> bool:
    """dummy test function always returns True"""
    return True


def env_var(name: str) -> str:
    """return environment variable"""
    return f"${{{name}}}"


def check_output(cmd: str) -> Optional[str]:
    """Run a command and return its output, or None if command not found"""
    try:
        return subprocess.check_output(cmd.split(), encoding="utf8").strip()
    except FileNotFoundError:
        return None


# -----------------------------------------------------------------------------
# utility classes


class UniqueList(list):
    """A list subclass of unique elements."""

    def __init__(self, iterable=None):
        """Initialize UniqueList, ensuring all elements are unique."""
        super().__init__()
        if iterable is not None:
            for item in iterable:
                self.add(item)

    def __repr__(self):
        """Custom representation showing it's a UniqueList."""
        return f"UniqueList({super().__repr__()})"

    def __iadd__(self, other):
        """Override += operator to maintain uniqueness."""
        self.extend(other)
        return self

    def __add__(self, other):
        """Override + operator to return a new UniqueList."""
        result = UniqueList(self)
        result.extend(other)
        return result

    def add(self, item):
        """Add an item only if it's not already in the list."""
        if item not in self:
            self.append(item)
        return self

    def append(self, item):
        """Override append to maintain uniqueness."""
        if item not in self:
            super().append(item)

    def extend(self, iterable):
        """Override extend to maintain uniqueness."""
        for item in iterable:
            self.add(item)

    def insert(self, index, item):
        """Override insert to maintain uniqueness."""
        if item not in self:
            super().insert(index, item)

    def first(self):
        """Get first item if it exists"""
        return self[0]

    def last(self):
        """Get last item if it exists"""
        return self[-1]


# -----------------------------------------------------------------------------
# variable classes


class Var:
    """Recursively Expanded Variable"""

    assign_op = "="

    def __init__(self, key: str, *values):
        self.key = key
        if not values:
            raise ValueError("must enter at least one value")
        self.value = values[0] if len(values) == 1 else "\n".join(values)

    def __str__(self):
        if "\n" in self.value:
            lines = self.value.split("\n")
            values = "\n".join(lines)
            if VERSION > 3.81:
                return f"define {self.key} {self.assign_op}\n{values}\nendef\n"
            else:
                return f"define {self.key}\n{values}\nendef\n"
        return f"{self.key} {self.assign_op} {self.value}"


class SVar(Var):
    """Simply Expanded Variable"""

    assign_op = ":="


class IVar(Var):
    """Immediately Expanded Variable"""

    assign_op = ":::="


class CVar(Var):
    """Conditional Variable"""

    assign_op = "?="


class AVar(Var):
    """Appended Variable"""

    assign_op = "+="


# -----------------------------------------------------------------------------
# main classes


class MakefileWriter:
    """Handles writing Makefile contents"""

    def __init__(self, path: PathLike):
        self.makefile = open(path, "w", encoding="utf8")

    def write(self, line: str = "") -> None:
        """Write a line to the Makefile"""
        print(line, file=self.makefile)

    def close(self) -> None:
        """Close the Makefile"""
        self.makefile.close()


class PythonSystem:
    """Python system information"""

    def __init__(self):
        self.name = "Python"
        self.version_info = sys.version_info

    def __str__(self):
        return self.version

    @property
    def version(self) -> str:
        """semantic version of python: 3.11.10"""
        return f"{self.major}.{self.minor}.{self.patch}"

    @property
    def ver(self) -> str:
        """short major.minor python version: 3.11"""
        return f"{self.major}.{self.minor}"

    @property
    def ver_nodot(self) -> str:
        """concat major and minor version components: 311 in 3.11.7"""
        return self.ver.replace(".", "")

    @property
    def major(self) -> int:
        """major component of semantic version: 3 in 3.11.7"""
        return self.version_info.major

    @property
    def minor(self) -> int:
        """minor component of semantic version: 11 in 3.11.7"""
        return self.version_info.minor

    @property
    def patch(self) -> int:
        """patch component of semantic version: 7 in 3.11.7"""
        return self.version_info.micro

    @property
    def name_version(self) -> str:
        """return <name>-<fullversion>: e.g. Python-3.11.7"""
        return f"{self.name}-{self.version}"

    @property
    def name_ver(self) -> str:
        """return <name.lower><ver>: e.g. python3.11"""
        return f"{self.name.lower()}{self.ver}"

    @property
    def executable_name(self) -> str:
        """executable name"""
        name = self.name.lower()
        if PLATFORM == "Windows":
            name = f"{self.name}.exe"
        return name

    @property
    def libname(self) -> str:
        """library name prefix"""
        return f"lib{self.name}"

    @property
    def linklib(self) -> str:
        """name of library for linking"""
        return f"-l{self.name_ver}"

    @property
    def staticlib_name(self) -> str:
        """static libname"""
        suffix = ".a"
        if PLATFORM == "Windows":
            suffix = ".lib"
        return f"{self.libname}{suffix}"

    @property
    def dylib_name(self) -> str:
        """dynamic link libname"""
        if PLATFORM == "Windows":
            return f"{self.libname}.dll"
        if PLATFORM == "Darwin":
            return f"{self.libname}.dylib"
        return f"{self.libname}.so"

    @property
    def dylib_linkname(self) -> str:
        """symlink to dylib"""
        if PLATFORM == "Darwin":
            return f"{self.libname}.dylib"
        return f"{self.libname}.so"

    @property
    def prefix(self) -> str:
        """python system prefix"""
        return sysconfig.get_config_var("prefix")

    @property
    def include_dir(self) -> str:
        """python include directory"""
        return sysconfig.get_config_var("INCLUDEPY")

    @property
    def config_h_dir(self) -> str:
        """directory of config.h file"""
        return os.path.dirname(sysconfig.get_config_h_filename())

    @property
    def base_cflags(self) -> str:
        """python base cflags"""
        return sysconfig.get_config_var("BASECFLAGS")

    @property
    def libs(self) -> str:
        """python libs to link to"""
        return sysconfig.get_config_var("LIBS")

    @property
    def syslibs(self) -> str:
        """python system libs to link to"""
        return sysconfig.get_config_var("SYSLIBS")

    @property
    def is_shared(self) -> bool:
        """python system was built with enable_shared option"""
        return bool(sysconfig.get_config_var("Py_ENABLE_SHARED"))

    @property
    def libpl(self) -> str:
        """directory of python dependencies"""
        return sysconfig.get_config_var("LIBPL")

    @property
    def extension_suffix(self) -> str:
        """suffix of compiled python extension"""
        return sysconfig.get_config_var("EXT_SUFFIX")


class Builder:
    """Configure and execute compiler instructions."""

    def __init__(self, target: PathLike, strict: bool = False):
        self.target = target
        self.strict = strict  # raise error if entry already exists
        self._cc = "gcc"
        self._cxx = "g++"
        self._cppfiles: UniqueList = UniqueList()
        self._hppfiles: UniqueList = UniqueList()
        self._include_dirs: UniqueList = UniqueList()  # include directories
        self._cflags: UniqueList = UniqueList()  # c compiler flags
        self._cxxflags: UniqueList = UniqueList()  # c++ compiler flags
        self._link_dirs: UniqueList = UniqueList()  # link directories
        self._ldlibs: UniqueList = UniqueList()  # link libraries
        self._ldflags: UniqueList = UniqueList()  # linker flags + link_dirs
        self._cleanup_patterns: UniqueList = (
            UniqueList()
        )  # post-build cleanup by glob pattern
        self._cleanup_targets: UniqueList = UniqueList()  # post-build cleanup by path

    @property
    def cc(self) -> str:
        """c compiler"""
        return self._cc

    @cc.setter
    def cc(self, value: str) -> None:
        """set c compiler"""
        self._cc = value

    @property
    def cxx(self) -> str:
        """c++ compiler"""
        return self._cxx

    @cxx.setter
    def cxx(self, value: str) -> None:
        """set c++ compiler"""
        self._cxx = value

    @property
    def cppfiles(self) -> UniqueList:
        """c++ files"""
        return self._cppfiles

    @cppfiles.setter
    def cppfiles(self, value: list[str]) -> None:
        """set c++ files"""
        self._cppfiles = UniqueList(value)

    @property
    def hppfiles(self) -> UniqueList:
        """hpp files"""
        return self._hppfiles

    @hppfiles.setter
    def hppfiles(self, value: list[str]) -> None:
        """set hpp files"""
        self._hppfiles = UniqueList(value)

    @property
    def include_dirs(self) -> UniqueList:
        """include directories"""
        return self._include_dirs

    @include_dirs.setter
    def include_dirs(self, value: list[str]) -> None:
        """set include directories"""
        self._include_dirs = UniqueList(value)

    @property
    def cflags(self) -> UniqueList:
        """c compiler flags"""
        return self._cflags

    @cflags.setter
    def cflags(self, value: list[str]) -> None:
        """set c compiler flags"""
        self._cflags = UniqueList(value)

    @property
    def cxxflags(self) -> UniqueList:
        """c++ compiler flags"""
        return self._cxxflags

    @cxxflags.setter
    def cxxflags(self, value: list[str]) -> None:
        """set c++ compiler flags"""
        self._cxxflags = UniqueList(value)

    @property
    def link_dirs(self) -> UniqueList:
        """link directories"""
        return self._link_dirs

    @link_dirs.setter
    def link_dirs(self, value: list[str]) -> None:
        """set link directories"""
        self._link_dirs = UniqueList(value)

    @property
    def ldlibs(self) -> UniqueList:
        """link libraries"""
        return self._ldlibs

    @ldlibs.setter
    def ldlibs(self, value: list[str]) -> None:
        """set link libraries"""
        self._ldlibs = UniqueList(value)

    @property
    def ldflags(self) -> UniqueList:
        """linker flags"""
        return self._ldflags

    @ldflags.setter
    def ldflags(self, value: list[str]) -> None:
        """set linker flags"""
        self._ldflags = UniqueList(value)

    @property
    def cleanup_patterns(self) -> UniqueList:
        """cleanup post-build by glob pattern"""
        return self._cleanup_patterns

    @cleanup_patterns.setter
    def cleanup_patterns(self, value: list[str]) -> None:
        """set cleanup post-build by glob pattern"""
        self._cleanup_patterns = UniqueList(value)

    @property
    def cleanup_targets(self) -> UniqueList:
        """cleanup post-build by path"""
        return self._cleanup_targets

    @cleanup_targets.setter
    def cleanup_targets(self, value: list[str]) -> None:
        """set cleanup post-build by path"""
        self._cleanup_targets = UniqueList(value)

    @property
    def build_cmd(self) -> str:
        """Get the executable or extension build command"""
        return f"{self.CXX} {self.CXXFLAGS} {self.CPPFILES} {self.LDLIBS} {self.LDFLAGS} -o {self.TARGET}"

    @property
    def TARGET(self) -> str:
        """compilation product"""
        return str(self.target)

    @property
    def CPPFILES(self) -> str:
        """c++ files"""
        return " ".join(self.cppfiles)

    @property
    def HPPFILES(self) -> str:
        """hpp files"""
        return " ".join(self.hppfiles)

    @property
    def CXX(self) -> str:
        """c++ compiler"""
        return self.cxx

    @property
    def CFLAGS(self) -> str:
        """c compiler flags"""
        return " ".join(self.cflags)

    @property
    def CXXFLAGS(self) -> str:
        """c++ compiler flags"""
        _flags = " ".join(self.cxxflags)
        return f"{_flags} {self.INCLUDEDIRS}"

    @property
    def INCLUDEDIRS(self) -> str:
        """include directories"""
        return " ".join(self.include_dirs)

    @property
    def LINKDIRS(self) -> str:
        """link directories"""
        return " ".join(self.link_dirs)

    @property
    def LDFLAGS(self) -> str:
        """linker flags"""
        _flags = " ".join(self.ldflags)
        return f"{_flags} {self.LINKDIRS}"

    @property
    def LDLIBS(self) -> str:
        """link libraries"""
        return " ".join(self.ldlibs)

    def _add_config_entries(
        self,
        attr: str,
        prefix: str = "",
        test_func: Optional[TestFunc] = None,
        *entries,
    ) -> None:
        """Add an entry to the configuration"""
        assert hasattr(self, attr), f"Invalid attribute: {attr}"
        _list = getattr(self, attr)
        if not test_func:
            test_func = always_true
        for entry in entries:
            assert test_func(entry), f"Invalid entry: {entry}"
            if entry in _list:
                if self.strict:
                    raise ValueError(f"entry: {entry} already exists in {attr} list")
                continue
            _list.append(f"{prefix}{entry}")

    def _execute(self, cmd: str) -> None:
        """Execute a command"""
        print(cmd)
        os.system(cmd)

    def _remove(self, path: PathLike) -> None:
        """Remove a target"""
        path = Path(path)
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=False)
        else:
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def configure(self) -> None:
        """Configure the builder"""
        self._setup_defaults()

    def build(self, dry_run: bool = False) -> None:
        """configure, then build executable or extension"""
        self.configure()
        if dry_run:
            print(self.build_cmd)
        else:
            print()
            self._execute(self.build_cmd)
            if self.cleanup_patterns or self.cleanup_targets:
                self.clean()

    def clean(self) -> None:
        """Clean up build artifacts"""
        for pattern in self.cleanup_patterns:
            for path in Path(".").glob(pattern):
                self._remove(path)
        for target in self.cleanup_targets:
            self._remove(target)

    def run_executable(self) -> None:
        """Run the executable"""
        print(f"Running {self.target}")
        self._execute(f"./{self.target}")

    def add_cppfiles(self, *entries: str) -> None:
        """Add c++ files to the configuration"""
        self._add_config_entries("_cppfiles", "", None, *entries)

    def add_hppfiles(self, *entries: str) -> None:
        """Add hpp files to the configuration"""
        self._add_config_entries("_hppfiles", "", None, *entries)

    def add_include_dirs(self, *entries):
        """Add include directories to the configuration"""
        self._add_config_entries("_include_dirs", "-I", os.path.isdir, *entries)

    def add_cflags(self, *entries):
        """Add compiler flags to the configuration"""
        self._add_config_entries("_cflags", "", None, *entries)

    def add_cxxflags(self, *entries):
        """Add c++ compiler flags to the configuration"""
        self._add_config_entries("_cxxflags", "", None, *entries)

    def add_link_dirs(self, *entries):
        """Add link directories to the configuration"""
        self._add_config_entries("_link_dirs", "-L", os.path.isdir, *entries)

    def add_ldlibs(self, *entries):
        """Add link libraries to the configuration"""
        self._add_config_entries("_ldlibs", "", None, *entries)

    def add_ldflags(self, *entries):
        """Add linker flags to the configuration"""
        self._add_config_entries("_ldflags", "", None, *entries)

    def add_cleanup_patterns(self, *entries):
        """Add cleanup patterns to the configuration"""
        self._add_config_entries("_cleanup_patterns", "", None, *entries)

    def add_cleanup_targets(self, *entries):
        """Add cleanup targets to the configuration"""
        self._add_config_entries("_cleanup_targets", "", None, *entries)

    def _setup_defaults(self):
        """Setup default model configuration"""
        self.add_include_dirs(os.getcwd())


class MakefileGenerator:
    """Generates Makefile for C/C++ code"""

    def __init__(self, path: PathLike, strict: bool = False):
        self.path = path
        self.strict = strict  # raise error if variable or entry already exists
        self.cxx = "g++"
        self.vars: dict[str, PathLike] = {}  # variables
        self.var_order: UniqueList = UniqueList()  # write order of variables
        self.include_dirs: UniqueList = UniqueList()  # include directories
        self.cflags: UniqueList = UniqueList()  # c compiler flags
        self.cxxflags: UniqueList = UniqueList()  # c++ compiler flags
        self.link_dirs: UniqueList = UniqueList()  # link directories
        self.ldlibs: UniqueList = UniqueList()  # link libraries
        self.ldflags: UniqueList = UniqueList()  # linker flags + link_dirs
        self.targets: UniqueList = UniqueList()  # targets
        self.pattern_rules: UniqueList = (
            UniqueList()
        )  # pattern rules (e.g., %.o: %.cpp)
        self.phony: UniqueList = UniqueList()  # phony targets
        self.clean: UniqueList = UniqueList()  # clean target
        # writer
        self.writer = MakefileWriter(path)

    def write(self, text: Optional[str] = None) -> None:
        """Write a line to the Makefile"""
        if not text:
            self.writer.write("")
        else:
            self.writer.write(text)

    def close(self) -> None:
        """Close the Makefile"""
        self.writer.close()

    def check_dir(self, path: PathLike) -> bool:
        """Check if a path is a valid directory"""
        defaults = {"HOME": "$(HOME)", "PWD": "$(PWD)", "CURDIR": "$(CURDIR)"}
        str_path = str(path)
        # check if path contains a variable
        # FIXME: should check for multiple variables
        if str(path) in defaults.values():
            return True
        match = re.match(r".*\$+\((.+)\).*", str_path)
        if match:
            key = match.group(1)
            if key in defaults:
                return True
            assert key in self.vars, f"Invalid variable: {key}"
            assert os.path.isdir(self.vars[key]), (
                f"Value of variable {key} is not a directory: {self.vars[key]}"
            )
            return True
        return os.path.isdir(str_path)

    def _normalize_path(self, path: str) -> str:
        """Normalize a path"""
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        return path.replace(cwd, "$(CURDIR)").replace(home, "$(HOME)")

    def _normalize_paths(self, filenames: UniqueList) -> UniqueList:
        """Replace filenames with current directory"""
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        return UniqueList(
            [f.replace(cwd, "$(CURDIR)").replace(home, "$(HOME)") for f in filenames]
        )

    def _add_entry_or_variable(
        self,
        attr: str,
        prefix: str = "",
        test_func: Optional[TestFunc] = None,
        *entries,
        **kwargs,
    ) -> None:
        """Add an entry or variable to the Makefile"""
        assert hasattr(self, attr), f"Invalid attribute: {attr}"
        _list = getattr(self, attr)
        if not test_func:
            test_func = always_true
        for entry in entries:
            assert test_func(entry), f"Invalid entry: {entry}"
            if entry in _list:
                if self.strict:
                    raise ValueError(f"entry: {entry} already exists in {attr} list")
                continue
            _list.append(f"{prefix}{entry}")
        for key, value in kwargs.items():
            assert test_func(value), f"Invalid value: {value}"
            if key in self.vars:
                if self.strict:
                    raise ValueError(f"variable: {key} already exists in vars dict")
                continue
            self.vars[key] = Var(key, value)
            _list.append(f"{prefix}$({key})")
            self.var_order.append(key)

    def add_var(self, var: Var) -> None:
        """Add a variable to the Makefile"""
        self.vars[var.key] = var
        self.var_order.append(var.key)

    def add_variable(self, key: str, value: str, var_type=Var) -> None:
        """Add a variable to the Makefile"""
        self.vars[key] = var_type(key, value)
        self.var_order.append(key)

    def add_include_dirs(self, *entries, **kwargs):
        """Add include directories to the Makefile"""
        self._add_entry_or_variable(
            "include_dirs", "-I", self.check_dir, *entries, **kwargs
        )

    def add_cflags(self, *entries, **kwargs):
        """Add compiler flags to the Makefile"""
        self._add_entry_or_variable("cflags", "", None, *entries, **kwargs)

    def add_cxxflags(self, *entries, **kwargs):
        """Add c++ compiler flags to the Makefile"""
        self._add_entry_or_variable("cxxflags", "", None, *entries, **kwargs)

    def add_link_dirs(self, *entries, **kwargs):
        """Add link directories to the Makefile"""
        self._add_entry_or_variable(
            "link_dirs", "-L", self.check_dir, *entries, **kwargs
        )

    def add_ldlibs(self, *entries, **kwargs):
        """Add link libraries to the Makefile"""
        self._add_entry_or_variable("ldlibs", "", None, *entries, **kwargs)

    def add_ldflags(self, *entries, **kwargs):
        """Add linker flags to the Makefile"""
        self._add_entry_or_variable("ldflags", "", None, *entries, **kwargs)

    def add_target(
        self, name: str, recipe: Optional[str] = None, deps: Optional[list[str]] = None
    ):
        """Add targets to the Makefile"""
        if not recipe and not deps:
            raise ValueError("Either recipe or dependencies must be provided")
        if recipe and deps:
            _deps = " ".join(deps)
            _target = f"{name}: {_deps}\n\t{recipe}"
        elif recipe and not deps:
            _target = f"{name}:\n\t{recipe}"
        elif not recipe and deps:
            _deps = " ".join(deps)
            _target = f"{name}: {_deps}"
        if _target in self.targets:
            raise ValueError(f"target: '{_target}' already exists in `targets` list")
        self.targets.append(_target)

    def add_pattern_rule(self, target_pattern: str, source_pattern: str, recipe: str):
        """Add a pattern rule to the Makefile (e.g., %.o: %.cpp)"""
        if not target_pattern or not source_pattern or not recipe:
            raise ValueError(
                "target_pattern, source_pattern, and recipe are all required"
            )
        if "%" not in target_pattern:
            raise ValueError("target_pattern must contain '%' wildcard")
        if "%" not in source_pattern:
            raise ValueError("source_pattern must contain '%' wildcard")

        pattern_rule = f"{target_pattern}: {source_pattern}\n\t{recipe}"
        if pattern_rule in self.pattern_rules:
            raise ValueError(f"pattern rule: '{pattern_rule}' already exists")
        self.pattern_rules.append(pattern_rule)

    def add_phony(self, *entries):
        """Add phony targets to the Makefile"""
        for entry in entries:
            if entry and entry not in self.phony:
                self.phony.append(entry)

    def add_clean(self, *entries):
        """Add clean target to the Makefile"""
        for entry in entries:
            if entry and entry not in self.clean:
                self.clean.append(entry)

    def _setup_defaults(self):
        """Setup default model configuration"""
        self.add_include_dirs(
            "$(CURDIR)"
        )  # CURDIR is absolute path to the current directory

    def _write_filelist(self, name: str, files: UniqueList) -> None:
        """Write a file list to the Makefile"""
        if not files:
            return
        if len(files) == 1:
            self.write(f"{name}={files[0]}")
        else:
            filelist = " \\\n\t".join(files)
            self.write(f"{name}=\\\n\t{filelist}\n")

    def _write_variables(self) -> None:
        """Write variables to the Makefile"""
        self.write("# project variables")
        for key in self.var_order:
            var = self.vars[key]
            self.write(f"{var}")
        self.write()

        # write includes
        if self.include_dirs:
            include_dirs = " ".join(self.include_dirs)
            self.write(f"INCLUDEDIRS = {include_dirs}")
        # write link_dirs
        if self.link_dirs:
            link_dirs = " ".join(self.link_dirs)
            self.write(f"LINKDIRS = {link_dirs}")
        self.write()

        # write cxx compiler
        self.write(f"CXX = {self.cxx}")
        # write cflags
        if self.cflags:
            cflags = " ".join(self.cflags)
            self.write(f"CFLAGS += {cflags} $(INCLUDEDIRS)")
        # write cxxflags
        if self.cxxflags:
            cxxflags = " ".join(self.cxxflags)
            self.write(f"CXXFLAGS += {cxxflags} $(INCLUDEDIRS)")
        # write ldflags / link_dirs
        if self.ldflags or self.link_dirs:
            ldflags = " ".join(self.ldflags)
            self.write(f"LDFLAGS += {ldflags} $(LINKDIRS)")
        # write ldlibs
        if self.ldlibs:
            ldlibs = " ".join(self.ldlibs)
            self.write(f"LDLIBS = {ldlibs}")
        self.write()

    def _write_phony(self) -> None:
        """Write phony targets to the Makefile"""
        if self.phony:
            phone_targets = " ".join(self.phony)
            self.write()
            self.write(f".PHONY: {phone_targets}")
            self.write()

    def _write_pattern_rules(self) -> None:
        """Write pattern rules to the Makefile"""
        if self.pattern_rules:
            self.write("# Pattern rules")
            for pattern_rule in self.pattern_rules:
                self.write(pattern_rule)
                self.write()

    def _write_targets(self) -> None:
        """Write targets to the Makefile"""
        for target in sorted(self.targets):
            self.write(target)
            self.write()

    def _write_clean(self) -> None:
        """Write clean target to the Makefile"""
        if self.clean:
            clean_targets = " ".join(self.clean)
            self.write(f"clean:\n\t@rm -rf {clean_targets}")
            self.write()

    def generate(self) -> None:
        """Generate the Makefile"""
        self._setup_defaults()
        self._write_variables()
        self._write_phony()
        self._write_pattern_rules()
        self._write_targets()
        self._write_clean()
        self.close()


# -----------------------------------------------------------------------------
# CLI functionality


def cmd_build(args) -> None:
    """Build command using Builder class"""
    builder = Builder(args.target)

    if args.cc:
        builder.cc = args.cc
    if args.cxx:
        builder.cxx = args.cxx
    if args.cppfiles:
        builder.add_cppfiles(*args.cppfiles)
    if args.include_dirs:
        builder.add_include_dirs(*args.include_dirs)
    if args.cflags:
        builder.add_cflags(*args.cflags)
    if args.cxxflags:
        # Handle comma-separated flags or individual flags
        flags = []
        for flag_group in args.cxxflags:
            if "," in flag_group:
                flags.extend(flag_group.split(","))
            else:
                flags.append(flag_group)
        builder.add_cxxflags(*flags)
    if args.link_dirs:
        builder.add_link_dirs(*args.link_dirs)
    if args.ldflags:
        builder.add_ldflags(*args.ldflags)
    if args.ldlibs:
        builder.add_ldlibs(*args.ldlibs)

    builder.build(dry_run=args.dry_run)


def cmd_makefile(args) -> None:
    """Generate Makefile using MakefileGenerator class"""
    generator = MakefileGenerator(args.output)

    if args.cxx:
        generator.cxx = args.cxx
    if args.include_dirs:
        generator.add_include_dirs(*args.include_dirs)
    if args.cflags:
        # Handle comma-separated flags or individual flags
        flags = []
        for flag_group in args.cflags:
            if "," in flag_group:
                flags.extend(flag_group.split(","))
            else:
                flags.append(flag_group)
        generator.add_cflags(*flags)
    if args.cxxflags:
        # Handle comma-separated flags or individual flags
        flags = []
        for flag_group in args.cxxflags:
            if "," in flag_group:
                flags.extend(flag_group.split(","))
            else:
                flags.append(flag_group)
        generator.add_cxxflags(*flags)
    if args.link_dirs:
        generator.add_link_dirs(*args.link_dirs)
    if args.ldflags:
        # Handle comma-separated flags or individual flags
        flags = []
        for flag_group in args.ldflags:
            if "," in flag_group:
                flags.extend(flag_group.split(","))
            else:
                flags.append(flag_group)
        generator.add_ldflags(*flags)
    if args.ldlibs:
        # Handle comma-separated libraries or individual libraries
        libs = []
        for lib_group in args.ldlibs:
            if "," in lib_group:
                libs.extend(lib_group.split(","))
            else:
                libs.append(lib_group)
        generator.add_ldlibs(*libs)

    # Add variables
    if args.variables:
        for var_def in args.variables:
            if "=" in var_def:
                key, value = var_def.split("=", 1)
                generator.add_variable(key.strip(), value.strip())

    # Add targets
    if args.targets:
        for target_def in args.targets:
            parts = target_def.split(":", 2)
            name = parts[0].strip()
            deps = (
                parts[1].strip().split()
                if len(parts) > 1 and parts[1].strip()
                else None
            )
            recipe = parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
            generator.add_target(name, recipe, deps)

    # Add pattern rules
    if args.pattern_rules:
        for pattern_def in args.pattern_rules:
            parts = pattern_def.split(":", 2)
            if len(parts) != 3:
                raise ValueError(
                    f"Pattern rule must have format 'target_pattern:source_pattern:recipe', got: {pattern_def}"
                )
            target_pattern = parts[0].strip()
            source_pattern = parts[1].strip()
            recipe = parts[2].strip()
            generator.add_pattern_rule(target_pattern, source_pattern, recipe)

    # Add phony targets
    if args.phony:
        generator.add_phony(*args.phony)

    # Add clean patterns
    if args.clean:
        generator.add_clean(*args.clean)

    generator.generate()
    print(f"Generated Makefile: {args.output}")


# fmt: off
def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="Makefile generator / direct compilation tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Direct compilation
  %(prog)s build myprogram --cppfiles main.cpp utils.cpp \\
    --include-dirs /usr/local/include --ldlibs pthread
  
  # Build with compiler flags (quote flags with spaces/dashes)
  %(prog)s build myprogram --cppfiles main.cpp \\
    --cxxflags "-O2" "-Wall" "-std=c++17" --dry-run
  
  # Generate Makefile with pattern rules
  %(prog)s makefile -o Makefile \\
    --include-dirs /usr/local/include --ldlibs pthread \\
    --pattern-rules "%%.o:%%.cpp:$(CXX) $(CXXFLAGS) -c $< -o $@" \\
    --targets "all:build test:" --targets "build:main.o:$(CXX) -o $@ $^"

    When using Makefile-type variables and patters via the commandline
    Escap dollars with a backslash.
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Build command
    build_parser = subparsers.add_parser('build', help='Direct compilation using Builder')
    bp = build_parser.add_argument
    bp('target', help='Output target name')
    bp('-c', '--cppfiles', nargs='*', help='C++ source files')
    bp('--cc', help='C compiler (default: gcc)')
    bp('--cxx', help='C++ compiler (default: g++)')
    bp('-I', '--include-dirs', nargs='*', help='Include directories')
    bp('--cflags', nargs='*', help='C compiler flags (space-separated)')
    bp('--cxxflags', nargs='*', help='C++ compiler flags (space-separated)')
    bp('-L', '--link-dirs', nargs='*', help='Link directories')
    bp('--ldflags', nargs='*', help='Linker flags (space-separated)')
    bp('-l', '--ldlibs', nargs='*', help='Link libraries (space-separated)')
    bp('--dry-run', action='store_true', help='Show command without executing')
    bp.set_defaults(func=cmd_build)
    
    # Makefile command
    makefile_parser = subparsers.add_parser('makefile', help='Generate Makefile using MakefileGenerator')
    mp = makefile_parser.add_argument
    mp('-o', '--output', default='Makefile', help='Output Makefile path')
    mp('--cxx', help='C++ compiler (default: g++)')
    mp('-I', '--include-dirs', nargs='*', help='Include directories')
    mp('--cflags', nargs='*', help='C compiler flags')
    mp('--cxxflags', nargs='*', help='C++ compiler flags')
    mp('-L', '--link-dirs', nargs='*', help='Link directories')
    mp('--ldflags', nargs='*', help='Linker flags')
    mp('-l', '--ldlibs', nargs='*', help='Link libraries')
    mp('-D', '--variables', nargs='*', help='Variables (KEY=VALUE format)')
    mp('-t', '--targets', nargs='*', help='Targets (name:deps:recipe format)')
    mp('-p', '--pattern-rules', nargs='*', help='Pattern rules (target_pattern:source_pattern:recipe format)')
    mp('--phony', nargs='*', help='Phony target names')
    mp('--clean', nargs='*', help='Clean patterns/files')
    mp.set_defaults(func=cmd_makefile)
    
    return parser
    # fmt: on

def main() -> None:
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        args.func(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
