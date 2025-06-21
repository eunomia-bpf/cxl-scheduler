# CXL Memory Microbenchmarks Makefile

# Compiler and flags
CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -pthread -O3
LDFLAGS = -pthread
NUMA_LDFLAGS = -lnuma

# Debug flags (use with 'make DEBUG=1')
ifdef DEBUG
    CXXFLAGS += -g -DDEBUG -O0
else
    CXXFLAGS += -DNDEBUG
endif

# Source files
SOURCES = double_bandwidth.cpp cxl_memory_test.cpp double_bandwidth_thread.cpp

# Target executables
TARGETS = double_bandwidth cxl_memory_test double_bandwidth_thread

# Installation directories
PREFIX ?= /usr/local
BINDIR = $(PREFIX)/bin

# Build directory
BUILDDIR = build

# Default target
.PHONY: all
all: $(TARGETS)

# Create build directory
$(BUILDDIR):
	mkdir -p $(BUILDDIR)

# Main targets
double_bandwidth: double_bandwidth.cpp | $(BUILDDIR)
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDFLAGS)
	@echo "Built $@ successfully"

cxl_memory_test: cxl_memory_test.cpp | $(BUILDDIR)
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDFLAGS) $(NUMA_LDFLAGS)
	@echo "Built $@ successfully"

double_bandwidth_thread: double_bandwidth_thread.cpp | $(BUILDDIR)
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDFLAGS)
	@echo "Built $@ successfully"

# Installation
.PHONY: install
install: $(TARGETS)
	@echo "Installing to $(BINDIR)..."
	install -d $(BINDIR)
	install -m 755 $(TARGETS) $(BINDIR)
	@echo "Installation complete"

# Uninstall
.PHONY: uninstall
uninstall:
	@echo "Uninstalling from $(BINDIR)..."
	for target in $(TARGETS); do \
		rm -f $(BINDIR)/$$target; \
	done
	@echo "Uninstallation complete"

# Clean targets
.PHONY: clean
clean:
	rm -f $(TARGETS)
	rm -f *.o
	rm -f core
	rm -rf $(BUILDDIR)
	@echo "Clean complete"

.PHONY: distclean
distclean: clean
	rm -f *.log
	rm -f bandwidth_results.txt
	rm -f *~
	@echo "Distclean complete"

# Testing targets
.PHONY: test
test: $(TARGETS)
	@echo "Running basic functionality tests..."
	@echo "Testing double_bandwidth (10 second test)..."
	./double_bandwidth -t 4 -d 10 -b 104857600 -r 0.5
	@echo ""
	@echo "Testing cxl_memory_test (10 second system memory test)..."
	./cxl_memory_test -m system -t 4 -d 10 -b 104857600 -r 0.5
	@echo ""
	@echo "Testing double_bandwidth_thread (10 second test)..."
	./double_bandwidth_thread -t 4 -d 10 -b 104857600 -r 0.5
	@echo "All tests completed successfully"

# Quick test with smaller parameters
.PHONY: quicktest
quicktest: $(TARGETS)
	@echo "Running quick tests (5 seconds each)..."
	./double_bandwidth -t 2 -d 5 -b 52428800 -r 0.5
	./cxl_memory_test -m system -t 2 -d 5 -b 52428800 -r 0.5
	./double_bandwidth_thread -t 2 -d 5 -b 52428800 -r 0.5
	@echo "Quick tests completed"

# Dependency checking
.PHONY: check-deps
check-deps:
	@echo "Checking dependencies..."
	@which $(CXX) > /dev/null || (echo "Error: $(CXX) not found"; exit 1)
	@$(CXX) --version
	@echo "Checking for numa library..."
	@pkg-config --exists libnuma || echo "Warning: libnuma not found via pkg-config"
	@echo "Checking for pthread support..."
	@echo '#include <pthread.h>' | $(CXX) -x c++ -pthread -c - -o /dev/null 2>/dev/null || \
		(echo "Error: pthread not supported"; exit 1)
	@echo "All dependencies OK"

# Show help
.PHONY: help
help:
	@echo "CXL Memory Microbenchmarks Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  all                 - Build all programs (default)"
	@echo "  double_bandwidth    - Build advanced bandwidth benchmark"
	@echo "  cxl_memory_test     - Build comprehensive CXL memory test"
	@echo "  double_bandwidth_thread - Build simple bandwidth benchmark"
	@echo "  install             - Install programs to $(BINDIR)"
	@echo "  uninstall           - Remove programs from $(BINDIR)"
	@echo "  clean               - Remove built files"
	@echo "  distclean           - Remove all generated files"
	@echo "  test                - Run basic functionality tests"
	@echo "  quicktest           - Run quick tests (5 seconds each)"
	@echo "  check-deps          - Check build dependencies"
	@echo "  help                - Show this help"
	@echo ""
	@echo "Variables:"
	@echo "  DEBUG=1             - Build with debug symbols and no optimization"
	@echo "  PREFIX=/path        - Installation prefix (default: /usr/local)"
	@echo "  CXX=compiler        - C++ compiler to use (default: g++)"
	@echo ""
	@echo "Examples:"
	@echo "  make                - Build all programs"
	@echo "  make DEBUG=1        - Build with debug information"
	@echo "  make install PREFIX=/opt/cxl - Install to /opt/cxl/bin"
	@echo "  make test           - Build and run tests"

# Check for specific program requirements
.PHONY: check-numa
check-numa:
	@echo "Checking NUMA support..."
	@if ! ldconfig -p | grep -q libnuma; then \
		echo "Warning: libnuma not found in library path"; \
		echo "Install with: sudo apt-get install libnuma-dev (Ubuntu/Debian)"; \
		echo "         or: sudo yum install numactl-devel (RHEL/CentOS)"; \
	else \
		echo "NUMA support OK"; \
	fi

# Show build information
.PHONY: info
info:
	@echo "Build Information:"
	@echo "  Compiler: $(CXX)"
	@echo "  Flags: $(CXXFLAGS)"
	@echo "  Link flags: $(LDFLAGS)"
	@echo "  NUMA flags: $(NUMA_LDFLAGS)"
	@echo "  Install prefix: $(PREFIX)"
	@echo "  Build dir: $(BUILDDIR)"
	@echo "  Targets: $(TARGETS)"

# Make targets depend on source files for proper rebuilding
double_bandwidth: double_bandwidth.cpp
cxl_memory_test: cxl_memory_test.cpp
double_bandwidth_thread: double_bandwidth_thread.cpp

# Phony targets
.PHONY: $(TARGETS) 