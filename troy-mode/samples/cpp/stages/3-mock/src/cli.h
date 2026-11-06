/// @file
/// The textstats command line.

#ifndef TEXTSTATS_CLI_H_
#define TEXTSTATS_CLI_H_

#include <ostream>
#include <string>
#include <vector>

namespace textstats {

/// Prints one "word count" line on out for each of the most frequent words
/// of a text file. args holds the file's path and, optionally, "--top N",
/// with N 10 by default. Returns 0, or 1 after a message on err when the
/// file cannot be read.
int Run(const std::vector<std::string>& args, std::ostream& out,
        std::ostream& err);

}  // namespace textstats

#endif  // TEXTSTATS_CLI_H_
