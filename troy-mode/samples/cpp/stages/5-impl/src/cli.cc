#include "cli.h"

#include <fstream>
#include <sstream>
#include <string>

#include "textstats/counting.h"

namespace textstats {

int Run(const std::vector<std::string>& args, std::ostream& out,
        std::ostream& err) {
  int top = 10;
  std::string path;
  for (size_t i = 0; i < args.size(); ++i) {
    if (args[i] == "--top" && i + 1 < args.size()) {
      top = std::stoi(args[++i]);
    } else {
      path = args[i];
    }
  }
  std::ifstream file(path);
  if (!file) {
    err << "textstats: cannot read " << path << "\n";
    return 1;
  }
  std::stringstream text;
  text << file.rdbuf();
  for (const auto& [word, count] : TopWords(CountWords(text.str()), top)) {
    out << word << " " << count << "\n";
  }
  return 0;
}

}  // namespace textstats
