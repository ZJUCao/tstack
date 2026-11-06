// Tests of F01 Word counts: textstats::CountWords and textstats::TopWords.

#include "textstats/counting.h"

#include <gtest/gtest.h>

#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace textstats {
namespace {

using Counts = std::map<std::string, int>;
using Ranking = std::vector<std::pair<std::string, int>>;

// F01-T01: the same word in a different case is the same word.
TEST(CountWords, F01_T01_CaseDoesNotMatter) {
  EXPECT_EQ(CountWords("The cat saw the CAT"),
            (Counts{{"the", 2}, {"cat", 2}, {"saw", 1}}));
}

// F01-T02: punctuation splits words, and an apostrophe inside a word does
// not. A text without letters has no words.
TEST(CountWords, F01_T02_PunctuationSplitsWords) {
  EXPECT_EQ(CountWords("Don't stop, don't!"),
            (Counts{{"don't", 2}, {"stop", 1}}));
  EXPECT_EQ(CountWords("42 ..."), Counts{});
}

// F01-T03: most frequent first, equal counts in alphabetical order, at most
// n.
TEST(TopWords, F01_T03_MostFrequentFirst) {
  Counts counts{{"b", 2}, {"a", 2}, {"c", 3}, {"d", 1}};
  EXPECT_EQ(TopWords(counts, 3), (Ranking{{"c", 3}, {"a", 2}, {"b", 2}}));
}

// F01-T04: n below 1 is rejected.
TEST(TopWords, F01_T04_NBelowOneIsRejected) {
  EXPECT_THROW(TopWords(Counts{{"a", 1}}, 0), std::invalid_argument);
}

}  // namespace
}  // namespace textstats
