/// @file
/// The exception that a mock's function bodies throw (F03 design 4.2).

#ifndef TROY_NOT_IMPLEMENTED_H_
#define TROY_NOT_IMPLEMENTED_H_

#include <stdexcept>

namespace troy {

/// Thrown by a mock's function body until the function is implemented, so
/// every test of a new interface fails against the mock (R09). A mock body
/// is `throw troy::NotImplemented{};`.
class NotImplemented : public std::logic_error {
 public:
  /// Creates the exception with the message "not implemented".
  NotImplemented() : std::logic_error("not implemented") {}
};

}  // namespace troy

#endif  // TROY_NOT_IMPLEMENTED_H_
