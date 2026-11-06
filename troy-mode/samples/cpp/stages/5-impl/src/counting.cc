#include "textstats/counting.h"

#include <algorithm>
#include <cctype>
#include <regex>
#include <stdexcept>

namespace textstats {

std::map<std::string, int> CountWords(std::string_view text) {
  std::string lower(text);
  std::transform(
      lower.begin(), lower.end(), lower.begin(),
      [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
  const std::regex word("[a-z]+(?:'[a-z]+)*");
  std::map<std::string, int> counts;
  for (auto it = std::sregex_iterator(lower.begin(), lower.end(), word);
       it != std::sregex_iterator(); ++it) {
    ++counts[it->str()];
  }
  return counts;
}

std::vector<std::pair<std::string, int>> TopWords(
    const std::map<std::string, int>& counts, int n) {
  if (n < 1) {
    throw std::invalid_argument("n must be at least 1, not " +
                                std::to_string(n));
  }
  std::vector<std::pair<std::string, int>> ranked(counts.begin(), counts.end());
  std::stable_sort(
      ranked.begin(), ranked.end(),
      [](const auto& a, const auto& b) { return a.second > b.second; });
  ranked.resize(std::min(ranked.size(), static_cast<size_t>(n)));
  return ranked;
}

}  // namespace textstats
