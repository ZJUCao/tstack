#include "textstats/counting.h"

#include "troy/not_implemented.h"

namespace textstats {

std::map<std::string, int> CountWords(std::string_view /*text*/) {
  throw troy::NotImplemented{};
}

std::vector<std::pair<std::string, int>> TopWords(
    const std::map<std::string, int>& /*counts*/, int /*n*/) {
  throw troy::NotImplemented{};
}

}  // namespace textstats
