
from makefilegen import Var, Builder, MakefileGenerator

# Run tests if no CLI arguments
def test_builder() -> None:
    """Test Builder"""
    b = Builder("product")
    b.add_include_dirs("/opt/homebrew/include")
    b.add_cxxflags()
    b.add_cxxflags("-Wall", "-Wextra", "-std=c++11", "-O3")
    b.add_ldflags("-shared", "-Wl,-rpath,/usr/local/lib", "-fPIC")
    b.add_link_dirs("/usr/lib", "/usr/local/lib")
    b.add_ldlibs("-lpthread")
    b.build(dry_run=True)

def test_makefile_generator() -> None:
    """Test MakefileGenerator"""
    m = MakefileGenerator("/tmp/Makefile")
    m.add_var(Var("make_echos", "@echo 1", "@echo 2"))
    m.add_variable("TEST", "test")
    m.add_include_dirs("/opt/homebrew/include")
    m.add_cflags("-Wall", "-Wextra")
    m.add_cxxflags("-Wall", "-Wextra", "-std=c++11", "-O3")
    m.add_ldflags("-shared", "-Wl,-rpath,/usr/local/lib", "-fPIC")
    m.add_link_dirs("/usr/lib", "/usr/local/lib")
    m.add_ldlibs("-lpthread")
    m.add_target("all", deps=["build", "test"])
    m.add_target("build", deps=["tool.exe"])
    m.add_target(
        "tool.exe",
        "$(CXX) $(CPPFILES) $(CXXFLAGS) $(LDFLAGS) -o $@ $^",
        deps=["a.o", "b.o"],
    )
    m.add_target("test", "echo $(TEST)", deps=["test.o"])
    m.add_target("dump", "$(make_echos)")
    m.add_pattern_rule("%%.o", "%%.cpp", "$(CXX) $(CXXFLAGS) -c $< -o $@")
    m.add_phony("all", "build", "test", "dump")
    m.add_clean("test.o", "*.o")
    m.generate()
