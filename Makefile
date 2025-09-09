# project variables
define make_echos
@echo 1
@echo 2
endef

TEST = test

INCLUDEDIRS = -I/opt/homebrew/include -I$(CURDIR)
LINKDIRS = -L/usr/lib -L/usr/local/lib

CXX = g++
CFLAGS += -Wall -Wextra $(INCLUDEDIRS)
CXXFLAGS += -Wall -Wextra -std=c++11 -O3 $(INCLUDEDIRS)
LDFLAGS += -shared -Wl,-rpath,/usr/local/lib -fPIC $(LINKDIRS)
LDLIBS = -lpthread


.PHONY: all build test dump

all: build test

build: tool.exe

dump:
	$(make_echos)

test: test.o
	echo $(TEST)

tool.exe: a.o b.o
	$(CXX) $(CPPFILES) $(CXXFLAGS) $(LDFLAGS) -o $@ $^

clean:
	@rm -rf test.o *.o

