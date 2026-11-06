#include "cli.h"

#include "troy/not_implemented.h"

namespace textstats {

int Run(const std::vector<std::string>& /*args*/, std::ostream& /*out*/,
        std::ostream& /*err*/) {
  throw troy::NotImplemented{};
}

}  // namespace textstats
