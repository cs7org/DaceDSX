# Compiler and Tools
CC        = /usr/bin/g++
CXXFLAGS  = -fPIC -DRTI_USES_STD_FSTREAM -fpermissive -std=c++17 -w -Ofast \
             -I/usr/local/include/librdkafka \
             -I/home/mohamed/Desktop/DaceDS/DaceDS4energy-main/CppBaseWrapper/src \
             -I$(SUMO_HOME)/src \
             -I/home/mohamed/Desktop/DaceDS/
             
LDFLAGS   = -L/home/mohamed/Desktop/DaceDS/DaceDS4energy-main/CppBaseWrapper/lib -lstdc++fs -pthread \
             -L/home/mohamed/Desktop/DaceDS/libserdes/src-cpp -lserdes++ \
             -L/home/mohamed/Desktop/DaceDS/libserdes/src -lserdes \
             -L$(SUMO_HOME)/bin -lsumocpp \
             -L$(SUMO_HOME)/bin -ltracicpp

# Libraries to link
LDLIBS = -lsimwrapper -lpugixml -lsumocpp -ltracicpp

# Paths
SRC_DIR   = src
BIN_DIR   = .
OBJ_DIR   = obj

# Source files
SRCS = \
    $(SRC_DIR)/PrepareRun.cpp \
    $(SRC_DIR)/SumoWrapper.cpp \
    $(SRC_DIR)/api/InteractionImpl.cpp \
    $(SRC_DIR)/api/OrchestrationImpl.cpp \
    $(SRC_DIR)/api/ProvisionImpl.cpp \
    $(SRC_DIR)/api/SumoConnectionLibSUMO.cpp \
    $(SRC_DIR)/api/SumoObserver.cpp \
    $(SRC_DIR)/logic/SumoSimulationControl.cpp

# Object files
OBJS = $(SRCS:$(SRC_DIR)/%.cpp=$(OBJ_DIR)/%.o)

# Final binary
TARGET = $(BIN_DIR)/SumoWrapper

# Default target
all: $(BIN_DIR) $(OBJ_DIR) $(TARGET)

# Create bin/ and obj/ if not exist
$(BIN_DIR) $(OBJ_DIR):
	mkdir -p $@

# How to build the final binary
$(TARGET): $(OBJS)
	$(CC) $(CXXFLAGS) -o $@ $^ $(LDFLAGS) $(LDLIBS)

# How to compile .cpp into .o
$(OBJ_DIR)/%.o: $(SRC_DIR)/%.cpp
	mkdir -p $(dir $@)
	$(CC) $(CXXFLAGS) -c $< -o $@

# Clean build
clean:
	rm -rf $(OBJ_DIR) $(BIN_DIR)/SumoWrapper

.PHONY: all clean

