// Tests of F01 Word counts: the textstats command line.

#include "cli.h"

#include <gtest/gtest.h>

#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>

namespace textstats {
namespace {

// Inside a TEST body, a plain Run would name the test's own Run method,
// so the calls below spell out textstats::Run.

// F01-T05: Run prints a "word count" line per word and returns 0.
TEST(Run, F01_T05_PrintsMostFrequentWords) {
  std::filesystem::path path =
      std::filesystem::temp_directory_path() / "textstats_f01_t05.txt";
  std::ofstream(path) << "b a b c b a";
  std::ostringstream out;
  std::ostringstream err;
  EXPECT_EQ(textstats::Run({path.string(), "--top", "2"}, out, err), 0);
  EXPECT_EQ(out.str(), "b 3\na 2\n");
  std::filesystem::remove(path);
}

// F01-T06: a file that cannot be read gives a message on err and exit code 1.
TEST(Run, F01_T06_UnreadableFileIsReported) {
  std::ostringstream out;
  std::ostringstream err;
  EXPECT_EQ(textstats::Run({"no/such/file.txt"}, out, err), 1);
  EXPECT_NE(err.str().find("no/such/file.txt"), std::string::npos);
  EXPECT_EQ(out.str(), "");
}

}  // namespace
}  // namespace textstats
