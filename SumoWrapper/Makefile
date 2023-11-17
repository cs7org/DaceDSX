CC = g++
CFLAGS = -Wall

HeadersCPPWRAPPER = -I ../CppBaseWrapper/src/
HeadersLIBRDKAFKA = -I ./librdkafka-master/src-cpp/
HeadersPUGIXML = -I ./pugixml-1.13/src/
HeadersSUMO = -I ./sumo-git/build/cmake-build/src
HeadersAVRO = -I ../../../Downloads/avro-master/avro-master/lang/c++
SUMOLIB =  -L$SUMO_HOME/bin -lsumocpp -L$SUMO_HOME/bin -ltracicpp
CPPWRAPPER = -L ../CppBaseWrapper/build -lCppBaseWrapper
LIBRDKAFKA =  -L ./librdkafka-master/src-cpp/ -lrdkafka++
PUGIXML = -L ./pugixml-1.13 -lpugixml
AVRO = -L ../../../Downloads/avro-master/avro-master/lang/c++/build/ -lavrocpp
SERDES = -L ./libserdes-8.0.0/src-cpp -lserdes++ -L./libserdes-8.0.0/src-cpp/libserdes++.a -L./libserdes-8.0.0/src -lserdes
SUMO = -I./sumo-git/src -I ./sumo-git/build/cmake-build/src ./sumo-git/src/utils/traci/TraCIAPI.cpp ./sumo-git/src/foreign/tcpip/socket.cpp ./sumo-git/src/foreign/tcpip/storage.cpp  ./src/SumoWrapper.cpp


all: my_program

my_program: ./src/SumoWrapper.cpp
	$(CC) $(CFLAGS) -DDEBUG -g -std=c++17 -o SumoWrapper -I. $(SUMO) -I ../CppBaseWrapper/src $(HeadersLIBRDKAFKA) $(HeadersPUGIXML)  $(SUMOLIB) $(CPPWRAPPER) $(LIBRDKAFKA) $(PUGIXML) $(AVRO) $(SERDES)


clean:
	rm -f my_program
