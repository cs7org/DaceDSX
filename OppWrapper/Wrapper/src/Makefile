###############################################################################
# 1. User Configuration
###############################################################################

# User-customizable paths (change these as needed)
DACE_ROOT         ?= /home/$(USER)/Desktop/DaceDSX
VEINS_ROOT        ?= $(DACE_ROOT)/veins-veins-5.1
WRAPPER_SRC_ROOT  ?= $(DACE_ROOT)/CppBaseWrapper/src
WRAPPER_LIB_DIR   ?= $(DACE_ROOT)/CppBaseWrapper/lib
SERDES_CPP_LIB    ?= $(DACE_ROOT)/libserdes/src-cpp
SERDES_C_LIB      ?= $(DACE_ROOT)/libserdes/src
SUMO_HOME         ?= /home/mohamed/Desktop/DaceDS/sumo
SUMO_ROOT         ?= $(SUMO_HOME)/src

###############################################################################
# 2. Project Settings
###############################################################################

TARGET            = $(LIB_PREFIX)Wrapper$(D)$(SHARED_LIB_SUFFIX)
TARGET_DIR        = .
PROJECT_OUTPUT_DIR = ../out
PROJECT_REL_PATH   = src
O                 = $(PROJECT_OUTPUT_DIR)/$(CONFIGNAME)/$(PROJECT_REL_PATH)

###############################################################################
# 3. Source Files
###############################################################################

OBJS = $(addprefix $(O)/OppWrapper/, \
    InteractionHandlerCommunication11p.o \
    OppInteractionImpl.o \
    OppProvisionImpl.o \
    OppWrapper.o \
    ProvisionHandlerCommunication11p.o \
    ScenarioManager.o \
    Scheduler.o \
    TriggerMsgApp.o \
)

MSGFILES =
SMFILES  =

###############################################################################
# 4. Include Paths
###############################################################################

INCLUDE_PATH = \
    -I$(WRAPPER_SRC_ROOT) \
    -I$(VEINS_ROOT)/src \
    -I$(DACE_ROOT) \
    -I$(SUMO_ROOT) \
    -I/usr/local/include/librdkafka \
    -I$(OMNETPP_INCL_DIR)

###############################################################################
# 5. Libraries
###############################################################################

LIBS = \
    -L$(WRAPPER_LIB_DIR) \
    -L$(VEINS_ROOT)/src \
    -L$(SERDES_CPP_LIB) -lserdes++ \
    -L$(SERDES_C_LIB)   -lserdes \
    -lsimwrapper -lavrocpp -lrdkafka++ -lcppkafka -lrdkafka -lveins$(D)

# rpath for runtime linking
ifneq ($(TOOLCHAIN_NAME),clangc2)
LIBS += -Wl,-rpath,$(abspath $(WRAPPER_LIB_DIR)) \
        -Wl,-rpath,$(abspath $(VEINS_ROOT)/src)
endif

###############################################################################
# 6. OMNeT++ Configuration
###############################################################################

ifneq ("$(OMNETPP_CONFIGFILE)","")
  CONFIGFILE = $(OMNETPP_CONFIGFILE)
else ifneq ("$(OMNETPP_ROOT)","")
  CONFIGFILE = $(OMNETPP_ROOT)/Makefile.inc
else
  CONFIGFILE = $(shell opp_configfilepath)
endif

ifeq ("$(wildcard $(CONFIGFILE))","")
  $(error Config file '$(CONFIGFILE)' does not exist -- add OMNeT++ to PATH)
endif

include $(CONFIGFILE)

OMNETPP_LIBS = -loppenvir$D $(KERNEL_LIBS) $(SYS_LIBS)

###############################################################################
# 7. Compiler and Linker Flags
###############################################################################

COPTS    = $(CFLAGS) $(IMPORT_DEFINES) -DVEINS_IMPORT -Dthread_EXPORT -pthread \
           $(INCLUDE_PATH)

CFLAGS  += -fpermissive -std=c++17
LDFLAGS += -pthread

MSGCOPTS = $(INCLUDE_PATH)
SMCOPTS  =

###############################################################################
# 8. Dependency Handling
###############################################################################

COPTS_FILE = $(O)/.last-copts
ifneq ("$(COPTS)","$(shell cat $(COPTS_FILE) 2>/dev/null || echo '')")
$(shell $(MKPATH) "$(O)" && echo "$(COPTS)" >$(COPTS_FILE))
endif

###############################################################################
# 9. Build Rules
###############################################################################

.PHONY: all clean cleanall depend msgheaders smheaders
.SUFFIXES: .cc

all: $(TARGET_DIR)/$(TARGET)

$(TARGET_DIR)/%: $(O)/%
	@mkdir -p $(TARGET_DIR)
	$(Q)$(LN) $< $@
ifeq ($(TOOLCHAIN_NAME),clangc2)
	$(Q)-$(LN) $(<:%.dll=%.lib) $(@:%.dll=%.lib)
endif

$(O)/$(TARGET): $(OBJS) $(EXTRA_OBJS) Makefile $(CONFIGFILE)
	@$(MKPATH) $(O)
	@echo "Creating shared library: $@"
	$(Q)$(SHLIB_LD) -o $@ $(OBJS) $(EXTRA_OBJS) $(AS_NEEDED_OFF) \
	    $(WHOLE_ARCHIVE_ON) $(LIBS) $(WHOLE_ARCHIVE_OFF) \
	    $(OMNETPP_LIBS) $(LDFLAGS)
	$(Q)$(SHLIB_POSTPROCESS) $@

$(O)/%.o: %.cc $(COPTS_FILE) | msgheaders smheaders
	@$(MKPATH) $(dir $@)
	$(qecho) "$<"
	$(Q)$(CXX) -c $(CXXFLAGS) $(COPTS) -o $@ $<

%_m.cc %_m.h: %.msg
	$(qecho) MSGC: $<
	$(Q)$(MSGC) -s _m.cc -MD -MP -MF $(O)/$(basename $<)_m.h.d $(MSGCOPTS) $?

%_sm.cc %_sm.h: %.sm
	$(qecho) SMC: $<
	$(Q)$(SMC) -c++ -suffix cc $(SMCOPTS) $?

msgheaders: $(MSGFILES:.msg=_m.h)
smheaders:  $(SMFILES:.sm=_sm.h)

###############################################################################
# 10. Clean Targets
###############################################################################

clean:
	$(qecho) "Cleaning $(TARGET)"
	$(Q)-rm -rf $(O)
	$(Q)-rm -f $(TARGET_DIR)/$(TARGET)
	$(Q)-rm -f $(TARGET_DIR)/$(TARGET:%.dll=%.lib)
	$(Q)-rm -f $(call opp_rwildcard, . , *_m.cc *_m.h *_sm.cc *_sm.h)

cleanall:
	$(Q)$(MAKE) -s clean MODE=release
	$(Q)$(MAKE) -s clean MODE=debug
	$(Q)-rm -rf $(PROJECT_OUTPUT_DIR)

# Include dependencies
-include $(OBJS:%=%.d) $(MSGFILES:%.msg=$(O)/%_m.h.d)

