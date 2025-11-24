#
# Makefile for P4 program compilation
#
TARGET_NAME=ts_pipeline

TOOLS_PATH=~/tools/
BUILD_TOOLS=$(TOOLS_PATH)p4_build.sh
P4_SRC=p4/$(TARGET_NAME).p4
BUILD_FLAGS=--with-tofino2

RUN_SWITCH=$(SDE)/run_switchd.sh

# launch p4 program build
run_switch: build
	$(RUN_SWITCH) -p $(TARGET_NAME) --arch tofino2

# build p4 program
build:
	$(BUILD_TOOLS) $(P4_SRC) $(BUILD_FLAGS)

clean:
	rm -rf build/ $(TARGET_NAME).p4.json

.PHONY: build clean
