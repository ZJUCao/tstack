# troy-mode C/C++ pack: build settings for the whole project (F03 design 9.1).
# Include it from the top-level CMakeLists.txt right after project().

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)
# No C++20 module scanning: its GCC flags stop clang-tidy, and troy-mode
# projects use headers.
set(CMAKE_CXX_SCAN_FOR_MODULES OFF)

# GoogleTest from its release archive, built with the project's own compiler,
# so MSYS2 GCC, Ubuntu's GCC, and MSVC can all link it (F03 design D25).
# It comes before the options below, so it gets neither coverage nor the
# project's warnings.
include(FetchContent)
FetchContent_Declare(googletest
  URL https://github.com/google/googletest/releases/download/v1.18.0/googletest-1.18.0.tar.gz
  URL_HASH SHA256=6e3191c1455468b3fc35a417fb565c1c5071aee1b7e7f85e30cf48a98d37d8b5
  EXCLUDE_FROM_ALL)
set(INSTALL_GTEST OFF CACHE BOOL "" FORCE)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)
include(GoogleTest)
enable_testing()

if(MSVC)
  add_compile_options(/W4 /permissive-)
else()
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# MinGW: link the GCC runtime statically, so a program never loads another
# GCC's libstdc++ DLL that comes first on the PATH, such as Git for Windows'.
if(MINGW)
  add_link_options(-static)
endif()

# Line and branch coverage with gcov, for R11 (F03 design D22).
option(TROY_COVERAGE "Measure coverage with gcov" OFF)
if(TROY_COVERAGE)
  if(NOT CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    message(FATAL_ERROR "TROY_COVERAGE needs GCC (F03 design D22).")
  endif()
  add_compile_options(--coverage -O0)
  add_link_options(--coverage)
endif()

# troy_add_test(<name> <source>... [LIBS <target>...])
# Builds a GoogleTest executable whose tests CTest runs one by one, so each
# test's name reaches the JUnit report (F03 design 4.1).
function(troy_add_test name)
  cmake_parse_arguments(PARSE_ARGV 1 ARG "" "" "LIBS")
  add_executable(${name} ${ARG_UNPARSED_ARGUMENTS})
  target_link_libraries(${name} PRIVATE ${ARG_LIBS} GTest::gtest_main)
  gtest_discover_tests(${name})
endfunction()
