/// @file
/// Word counts of a text.

#ifndef TEXTSTATS_COUNTING_H_
#define TEXTSTATS_COUNTING_H_

#include <map>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

/// Counts and ranks the words of a text.
namespace textstats {

/// Counts each word of a text, ignoring case and punctuation. A word is a
/// run of ASCII letters, with apostrophes allowed between letters. Returns
/// each word, in lowercase, mapped to how often it occurs.
std::map<std::string, int> CountWords(std::string_view text);

/// Lists up to n words from counts, most frequent first, with equal counts
/// in alphabetical order. Throws std::invalid_argument when n is less
/// than 1.
std::vector<std::pair<std::string, int>> TopWords(
    const std::map<std::string, int>& counts, int n);

}  // namespace textstats

#endif  // TEXTSTATS_COUNTING_H_
