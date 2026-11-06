cmake_minimum_required(VERSION 3.28)
project(textstats LANGUAGES C CXX)
include(cmake/troy.cmake)

add_library(counting src/counting.cc)
target_include_directories(counting PUBLIC include)

add_library(cli src/cli.cc)
target_include_directories(cli PUBLIC src)
target_link_libraries(cli PUBLIC counting)

add_executable(textstats src/main.cc)
target_link_libraries(textstats PRIVATE cli)

troy_add_test(textstats_test tests/counting_test.cc tests/cli_test.cc LIBS cli)
