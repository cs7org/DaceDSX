# Compiling SumoWrapper

## Compile SumoWrapper
1.	Install sumo (make sure to check out a release-tag from the sumo-git-repo)
* https://sumo.dlr.de/docs/Installing/
* https://sumo.dlr.de/docs/Installing/Linux_Build.html
* export CMAKE_PREFIX_PATH=path_to_sumo_build/sumo/build:$CMAKE_PREFIX_PATH
* Create an empty config.h file and add it to the build folder in sumo
* Install **SUMOLibraries** in the parent directory (`/../sumo`) using this [guide](https://github.com/DLR-TS/SUMOLibraries).
2.	Install missing libraries (Preferably in DaceDSX folder)
  - [Avro](https://github.com/apache/avro): Follow the [instructions](https://github.com/apache/avro/blob/main/lang/c++/README) for both `avro/lang/c++` and `avro/lang/c`.
  - [Libserdes](https://github.com/confluentinc/libserdes)
  - [Librdkafka](https://github.com/confluentinc/librdkafka)
  - [CppKafka](https://github.com/mfontanini/cppkafka)
  - [PugiXML](https://github.com/zeux/pugixml)

3. **Build Libraries**:
   - For **CppKafka** and **PugiXML**:
     ```bash
     mkdir build
     cd build
     cmake ..
     make -j5
     sudo make install
     ```
   - For **Librdkafka*# Introduction
* and **Libserdes**:
     ```bash
     ./configure (#modify the `configure` script to use C++17 if build issues occur)
     make -j5
     sudo make install
     ```
 
3.	Compile CppBaseWrapper (adapt files in `CMakeLists.txt`)

     ```bash
     mkdir build
     cd build
     cmake ..
     make -j5
     ```
  
4.	Compile SumoWrapper
* Adjust `Makefile`
* Run `make`
5. Install gnome-terminal: `sudo apt install gnome-terminal`
6. Make sure the paths in `_data\executables\SumoWrapper\run.sh` are correct before running a scenario