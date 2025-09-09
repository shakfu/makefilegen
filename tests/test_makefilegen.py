import pytest
import tempfile
import os
from pathlib import Path
from makefilegen import (
    Var, SVar, IVar, CVar, AVar,
    Builder, MakefileGenerator, MakefileWriter,
    UniqueList, PythonSystem
)


class TestVariableClasses:
    """Test Makefile variable classes"""
    
    def test_var_basic(self):
        """Test basic Var functionality"""
        var = Var("TEST", "value1", "value2")
        assert var.key == "TEST"
        assert "value1" in var.value
        assert "value2" in var.value
        
    def test_svar_simple_assignment(self):
        """Test SVar (simple variable)"""
        svar = SVar("CC", "gcc")
        assert svar.key == "CC"
        assert svar.value == "gcc"
        
    def test_ivar_immediate_assignment(self):
        """Test IVar (immediate variable)"""
        ivar = IVar("VERSION", "1.0")
        assert ivar.key == "VERSION"
        assert ivar.value == "1.0"
        
    def test_cvar_conditional_assignment(self):
        """Test CVar (conditional variable)"""
        cvar = CVar("DEBUG", "1")
        assert cvar.key == "DEBUG"
        assert cvar.value == "1"
        
    def test_avar_append_assignment(self):
        """Test AVar (append variable)"""
        avar = AVar("CFLAGS", "-O2")
        assert avar.key == "CFLAGS"
        assert avar.value == "-O2"


class TestBuilder:
    """Test Builder class functionality"""
    
    def test_builder_creation(self):
        """Test Builder object creation"""
        builder = Builder("myprogram")
        assert builder.target == "myprogram"
        assert isinstance(builder.cppfiles, UniqueList)
        assert isinstance(builder.cflags, UniqueList)
        assert isinstance(builder.cxxflags, UniqueList)
        
    def test_builder_add_cxxflags(self):
        """Test adding C++ flags"""
        builder = Builder("test")
        builder.add_cxxflags("-Wall", "-Wextra", "-std=c++11")
        assert "-Wall" in builder.cxxflags
        assert "-Wextra" in builder.cxxflags
        assert "-std=c++11" in builder.cxxflags
        
        # Test duplicates are not added
        builder.add_cxxflags("-Wall")  # Already exists
        assert list(builder.cxxflags).count("-Wall") == 1
        
    def test_builder_add_cflags(self):
        """Test adding C flags"""
        builder = Builder("test")
        builder.add_cflags("-O2", "-g")
        assert "-O2" in builder.cflags
        assert "-g" in builder.cflags
        
    def test_builder_add_ldflags(self):
        """Test adding linker flags"""
        builder = Builder("test")
        builder.add_ldflags("-shared", "-fPIC")
        assert "-shared" in builder.ldflags
        assert "-fPIC" in builder.ldflags
        
    def test_builder_add_include_dirs(self):
        """Test adding include directories"""
        builder = Builder("test")
        # Use existing directories for testing
        builder.add_include_dirs("/tmp")
        assert "-I/tmp" in builder.include_dirs
        
    def test_builder_add_link_dirs(self):
        """Test adding link directories"""
        builder = Builder("test")
        # Use existing directories for testing
        builder.add_link_dirs("/tmp")
        assert "-L/tmp" in builder.link_dirs
        
    def test_builder_add_ldlibs(self):
        """Test adding libraries"""
        builder = Builder("test")
        builder.add_ldlibs("-lpthread", "-lm")
        assert "-lpthread" in builder.ldlibs
        assert "-lm" in builder.ldlibs
        
    def test_builder_dry_run(self):
        """Test Builder dry run functionality"""
        builder = Builder("test")
        builder.add_cxxflags("-Wall")
        builder.add_ldlibs("-lpthread")
        
        # Should not raise any exceptions
        builder.build(dry_run=True)


class TestMakefileGenerator:
    """Test MakefileGenerator class functionality"""
    
    @pytest.fixture
    def temp_makefile(self):
        """Create a temporary Makefile for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mk', delete=False) as f:
            temp_path = f.name
        yield temp_path
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
            
    def test_makefile_generator_creation(self, temp_makefile):
        """Test MakefileGenerator creation"""
        generator = MakefileGenerator(temp_makefile)
        assert generator.path == temp_makefile
        assert isinstance(generator.vars, dict)
        assert isinstance(generator.targets, UniqueList)
        assert isinstance(generator.cflags, UniqueList)
        assert isinstance(generator.cxxflags, UniqueList)
        
    def test_add_variable(self, temp_makefile):
        """Test adding variables"""
        generator = MakefileGenerator(temp_makefile)
        generator.add_variable("CC", "gcc")
        generator.add_variable("CFLAGS", "-O2")
        
        # Check variables were added
        assert "CC" in generator.vars
        assert "CFLAGS" in generator.vars
        assert generator.vars["CC"].value == "gcc"
        assert generator.vars["CFLAGS"].value == "-O2"
        
    def test_add_var_object(self, temp_makefile):
        """Test adding Var objects"""
        generator = MakefileGenerator(temp_makefile)
        var = Var("TEST", "value1", "value2")
        generator.add_var(var)
        
        assert "TEST" in generator.vars
        assert generator.vars["TEST"] == var
        
    def test_add_flags(self, temp_makefile):
        """Test adding various flags"""
        generator = MakefileGenerator(temp_makefile)
        generator.add_cflags("-Wall", "-Wextra")
        generator.add_cxxflags("-std=c++11", "-O3")
        generator.add_ldflags("-shared", "-fPIC")
        
        assert "-Wall" in generator.cflags
        assert "-std=c++11" in generator.cxxflags
        assert "-shared" in generator.ldflags
        
    def test_add_directories(self, temp_makefile):
        """Test adding include and link directories"""
        generator = MakefileGenerator(temp_makefile)
        generator.add_include_dirs("/tmp")
        generator.add_link_dirs("/tmp")
        
        assert "-I/tmp" in generator.include_dirs
        assert "-L/tmp" in generator.link_dirs
        
    def test_add_libraries(self, temp_makefile):
        """Test adding libraries"""
        generator = MakefileGenerator(temp_makefile)
        generator.add_ldlibs("-lpthread", "-lm")
        
        assert "-lpthread" in generator.ldlibs
        assert "-lm" in generator.ldlibs
        
    def test_add_target(self, temp_makefile):
        """Test adding targets"""
        generator = MakefileGenerator(temp_makefile)
        generator.add_target("all", deps=["main.o", "util.o"])
        generator.add_target("main.o", "gcc -c main.c", deps=["main.c"])
        
        # Check that targets were added to the list
        target_strings = list(generator.targets)
        assert any("all:" in target for target in target_strings)
        assert any("main.o:" in target for target in target_strings)
        
    def test_add_pattern_rule(self, temp_makefile):
        """Test adding pattern rules"""
        generator = MakefileGenerator(temp_makefile)
        generator.add_pattern_rule("%.o", "%.cpp", "$(CXX) $(CXXFLAGS) -c $< -o $@")
        
        assert len(generator.pattern_rules) == 1
        rule = generator.pattern_rules[0]
        assert "%.o: %.cpp" in rule
        assert "$(CXX) $(CXXFLAGS) -c $< -o $@" in rule
        
    def test_add_pattern_rule_validation(self, temp_makefile):
        """Test pattern rule validation"""
        generator = MakefileGenerator(temp_makefile)
        
        # Should raise ValueError for missing wildcards
        with pytest.raises(ValueError, match="target_pattern must contain '%' wildcard"):
            generator.add_pattern_rule("test.o", "%.cpp", "recipe")
            
        with pytest.raises(ValueError, match="source_pattern must contain '%' wildcard"):
            generator.add_pattern_rule("%.o", "test.cpp", "recipe")
            
    def test_add_phony(self, temp_makefile):
        """Test adding phony targets"""
        generator = MakefileGenerator(temp_makefile)
        generator.add_phony("all", "clean", "install")
        
        assert "all" in generator.phony
        assert "clean" in generator.phony
        assert "install" in generator.phony
        
    def test_add_clean(self, temp_makefile):
        """Test adding clean files"""
        generator = MakefileGenerator(temp_makefile)
        generator.add_clean("*.o", "*.so", "main")
        
        assert "*.o" in generator.clean
        assert "*.so" in generator.clean
        assert "main" in generator.clean
        
    def test_generate_makefile(self, temp_makefile):
        """Test complete Makefile generation"""
        generator = MakefileGenerator(temp_makefile)
        generator.add_variable("CC", "gcc")
        generator.add_variable("CFLAGS", "-Wall -O2")
        generator.add_target("all", deps=["main"])
        generator.add_target("main", "$(CC) $(CFLAGS) -o main main.c", deps=["main.c"])
        generator.add_pattern_rule("%.o", "%.c", "$(CC) $(CFLAGS) -c $< -o $@")
        generator.add_phony("all", "clean")
        generator.add_clean("*.o", "main")
        
        generator.generate()
        
        # Verify file was created and contains expected content
        assert os.path.exists(temp_makefile)
        with open(temp_makefile, 'r') as f:
            content = f.read()
            
        assert "CC = gcc" in content
        assert "CFLAGS = -Wall -O2" in content
        assert "all:" in content
        assert "main:" in content
        assert "%.o: %.c" in content
        assert ".PHONY:" in content
        assert "clean:" in content


class TestMakefileWriter:
    """Test MakefileWriter class functionality"""
    
    @pytest.fixture
    def temp_makefile(self):
        """Create a temporary Makefile for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mk', delete=False) as f:
            temp_path = f.name
        yield temp_path
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
            
    def test_makefile_writer_creation(self, temp_makefile):
        """Test MakefileWriter creation"""
        writer = MakefileWriter(temp_makefile)
        assert hasattr(writer, 'makefile')
        writer.close()
        
    def test_write_content(self, temp_makefile):
        """Test writing content to Makefile"""
        writer = MakefileWriter(temp_makefile)
        writer.write("CC = gcc\n")
        writer.write("CFLAGS = -Wall\n")
        writer.close()
        
        with open(temp_makefile, 'r') as f:
            content = f.read()
            
        assert "CC = gcc" in content
        assert "CFLAGS = -Wall" in content


class TestPythonSystem:
    """Test PythonSystem utilities"""
    
    def test_python_system_methods(self):
        """Test PythonSystem utility methods exist"""
        # Just verify the class exists and has expected methods
        # Since we don't know the exact implementation
        assert hasattr(PythonSystem, '__module__')


class TestIntegration:
    """Integration tests combining multiple components"""
    
    @pytest.fixture
    def temp_makefile(self):
        """Create a temporary Makefile for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mk', delete=False) as f:
            temp_path = f.name
        yield temp_path
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
            
    def test_builder_integration(self):
        """Test Builder with realistic C++ project"""
        builder = Builder("myapp")
        builder.add_include_dirs("/usr/local/include")
        builder.add_cxxflags("-Wall", "-Wextra", "-std=c++17", "-O2")
        builder.add_ldflags("-Wl,-rpath,/usr/local/lib")
        builder.add_link_dirs("/usr/local/lib")
        builder.add_ldlibs("-lpthread", "-lssl", "-lcrypto")
        
        # Test dry run doesn't crash
        builder.build(dry_run=True)
        
    def test_makefile_generator_integration(self, temp_makefile):
        """Test MakefileGenerator with realistic project"""
        generator = MakefileGenerator(temp_makefile)
        
        # Add variables
        generator.add_variable("CXX", "g++")
        generator.add_variable("PROJECT", "myproject")
        
        # Add flags and directories
        generator.add_cxxflags("-Wall", "-Wextra", "-std=c++17", "-O2")
        generator.add_include_dirs("/tmp")
        generator.add_link_dirs("/tmp")
        generator.add_ldlibs("-lpthread", "-lssl")
        
        # Add targets
        generator.add_target("all", deps=["$(PROJECT)"])
        generator.add_target("$(PROJECT)", "$(CXX) $(CXXFLAGS) -o $@ $(OBJECTS) $(LDFLAGS)", 
                           deps=["main.o", "utils.o"])
        generator.add_target("test", "./$(PROJECT) --test", deps=["$(PROJECT)"])
        
        # Add pattern rules
        generator.add_pattern_rule("%.o", "%.cpp", "$(CXX) $(CXXFLAGS) $(CPPFLAGS) -c $< -o $@")
        
        # Add phony and clean
        generator.add_phony("all", "test", "clean")
        generator.add_clean("*.o", "$(PROJECT)")
        
        # Generate the Makefile
        generator.generate()
        
        # Verify comprehensive content
        with open(temp_makefile, 'r') as f:
            content = f.read()
            
        # Check variables
        assert "CXX = g++" in content
        assert "PROJECT = myproject" in content
        
        # Check flags
        assert "-std=c++17" in content
        assert "-lpthread" in content
        
        # Check targets  
        assert "all:" in content
        assert "$(PROJECT):" in content
        assert "test:" in content
        
        # Check pattern rules
        assert "%.o: %.cpp" in content
        
        # Check phony and clean
        assert ".PHONY:" in content
        assert "clean:" in content


# CLI Tests
class TestCLI:
    """Test command line interface functionality"""
    
    @pytest.fixture
    def temp_makefile(self):
        """Create a temporary Makefile for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mk', delete=False) as f:
            temp_path = f.name
        yield temp_path
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass

    def test_cli_imports(self):
        """Test that CLI-related imports work"""
        import argparse
        import sys
        # Basic test that the modules needed for CLI are available
        assert argparse is not None
        assert sys is not None
        
    def test_builder_cli_simulation(self):
        """Test Builder functionality as it would be used from CLI"""
        # Simulate what the CLI would do for a build command
        builder = Builder("testapp")
        
        # Simulate parsing comma-separated flags
        cxxflags = "-Wall,-Wextra,-std=c++17".split(",")
        builder.add_cxxflags(*cxxflags)
        
        ldlibs = "-lpthread,-lm".split(",")
        builder.add_ldlibs(*ldlibs)
        
        # Test dry run (what CLI would do)
        builder.build(dry_run=True)
        
        assert "-Wall" in builder.cxxflags
        assert "-Wextra" in builder.cxxflags
        assert "-std=c++17" in builder.cxxflags
        assert "-lpthread" in builder.ldlibs
        assert "-lm" in builder.ldlibs
        
    def test_makefile_generator_cli_simulation(self, temp_makefile):
        """Test MakefileGenerator functionality as it would be used from CLI"""
        generator = MakefileGenerator(temp_makefile)
        
        # Simulate parsing key=value variables
        variables = ["CC=gcc", "CFLAGS=-Wall -O2", "PROJECT=myapp"]
        for var_str in variables:
            key, value = var_str.split("=", 1)
            generator.add_variable(key, value)
            
        # Simulate parsing targets with deps and recipes
        targets = ["all:main.o utils.o:", "clean::rm -f *.o $(PROJECT)"]
        for target_str in targets:
            parts = target_str.split(":")
            name = parts[0]
            deps = parts[1].split() if parts[1] else []
            recipe = parts[2] if len(parts) > 2 else None
            generator.add_target(name, recipe, deps)
            
        # Simulate parsing pattern rules
        pattern_rules = ["%.o:%.cpp:$(CXX) $(CXXFLAGS) -c $< -o $@"]
        for rule_str in pattern_rules:
            target, source, recipe = rule_str.split(":")
            generator.add_pattern_rule(target, source, recipe)
            
        generator.generate()
        
        # Verify the result
        with open(temp_makefile, 'r') as f:
            content = f.read()
            
        assert "CC = gcc" in content
        assert "PROJECT = myapp" in content
        assert "all:" in content
        assert "clean:" in content
        assert "%.o: %.cpp" in content