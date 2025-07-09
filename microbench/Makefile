CXX = g++
CXXFLAGS = -std=c++17 -O3 -Wall -Wextra -pthread
LIBS = -lnuma

TARGET = double_bandwidth
SOURCES = double_bandwidth.cpp

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(SOURCES)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(SOURCES) $(LIBS)

clean:
	rm -f $(TARGET)

install-deps:
	@echo "Installing NUMA development libraries..."
	@echo "On Ubuntu/Debian: sudo apt-get install libnuma-dev"
	@echo "On RHEL/CentOS: sudo yum install numactl-devel"
	@echo "On Fedora: sudo dnf install numactl-devel"

help:
	@echo "Available targets:"
	@echo "  all         - Build the double_bandwidth executable"
	@echo "  clean       - Remove build artifacts"
	@echo "  install-deps - Show commands to install NUMA dependencies"
	@echo "  help        - Show this help message" 