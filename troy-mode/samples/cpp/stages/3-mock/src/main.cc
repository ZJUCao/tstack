/// @file
/// The textstats program.

#include <exception>
#include <iostream>
#include <string>
#include <vector>

#include "cli.h"

/// Runs textstats on the command line's arguments. Returns Run's exit code,
/// or 1 after a message when an error escapes it.
int main(int argc, char** argv) {
  try {
    return textstats::Run(std::vector<std::string>(argv + 1, argv + argc),
                          std::cout, std::cerr);
  } catch (const std::exception& error) {
    std::cerr << "textstats: " << error.what() << "\n";
    return 1;
  }
}
