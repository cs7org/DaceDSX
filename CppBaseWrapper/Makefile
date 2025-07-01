DACEDS = /home/mohamed/Desktop/DaceDS/

CC      = /usr/bin/g++
SRC     = $(DACEDS)/DaceDS4energy-main/CppBaseWrapper/src
LIB     = $(DACEDS)/DaceDS4energy-main/CppBaseWrapper/lib

CFLAGS  = -fPIC -fpermissive -std=c++17 -w -Ofast \
          -I$(SRC) -I/usr/local/include/librdkafka -I $(DACEDS)

SERDESCPP = $(DACEDS)/libserdes/src-cpp
SERDESC =  $(DACEDS)/libserdes/src

LDFLAGS = -rdynamic -lavrocpp -L$(SERDESCPP) -lserdes++ -pthread -lrdkafka++ -lcppkafka -L$(SERDESC) -lserdes -lrdkafka

SRCS = \
$(SRC)/api/Traffic/Micro/ProvisionHandlerTrafficMicro.cpp \
$(SRC)/communication/AvroHelper.cpp \
$(SRC)/communication/Consumer.cpp \
$(SRC)/communication/MessageHandler.cpp \
$(SRC)/communication/InteractionHandler.cpp \
$(SRC)/communication/kafka/KafkaConsumer.cpp \
$(SRC)/communication/kafka/KafkaProducer.cpp \
$(SRC)/communication/LogHandler.cpp \
$(SRC)/communication/OrchestrationHandler.cpp \
$(SRC)/communication/Producer.cpp \
$(SRC)/communication/ProvisionHandler.cpp \
$(SRC)/communication/TimeSyncHandler.cpp \
$(SRC)/logic/SimulationControl.cpp \
$(SRC)/logic/TimeSync.cpp \
$(SRC)/main/SimulationWrapper.cpp \
$(SRC)/util/Config.cpp \
$(SRC)/util/Utils.cpp

all:
	mkdir -p $(LIB)
	$(CC) -shared -o $(LIB)/libsimwrapper.so $(SRCS) $(CFLAGS) $(LDFLAGS)

clean:
	rm -rf *.o *.so $(LIB)/libsimwrapper.so

.PHONY: all clean

