cmake_minimum_required(VERSION 3.12)
project(CppBaseWrapper)

set(CMAKE_CXX_STANDARD 17)


file(GLOB SOURCES
    "src/api/Traffic/*.cpp"
    "src/*/*.cpp"
    "src/*/*/*.cpp"
    "../SumoWrapper/src/api/*.cpp"
    "../SumoWrapper/src/logic/*.cpp"
    "../SumoWrapper/src/PrepareRun.cpp"

)

add_library(CppBaseWrapper SHARED ${SOURCES})

target_include_directories(CppBaseWrapper PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

target_include_directories(CppBaseWrapper PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}             # Current directory
    ${CMAKE_CURRENT_SOURCE_DIR}/src         # Source directory
    ${CMAKE_CURRENT_SOURCE_DIR}/src/datamodel   # Directory containing datamodel headers
    ${CMAKE_CURRENT_SOURCE_DIR}/../SumoWrapper/librdkafka-master/src-cpp/   # Directory containing datamodel headers
    ${CMAKE_CURRENT_SOURCE_DIR}/../SumoWrapper/pugixml-1.13/src//   # Directory containing datamodel headers
    ${CMAKE_CURRENT_SOURCE_DIR}/../SumoWrapper/src


)

find_package(SUMO REQUIRED)
target_include_directories(CppBaseWrapper PUBLIC ${SUMO_INCLUDE_DIRS})

target_link_libraries(CppBaseWrapper SUMO::libsumocpp
)

target_include_directories(CppBaseWrapper PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/../SumoWrapper/sumo-git/src
    ${CMAKE_CURRENT_SOURCE_DIR}/../SumoWrapper/sumo-git/build/cmake-build/src
    )
