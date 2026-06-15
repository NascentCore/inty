# Fix bug

- Understand the bug provided
- Write tests to reproduce the bug according to the description
- Come up with initial fixing idea and ask me to confirm to proceed

## How to fix

- If the bug is caused by unhandled state, do not handle the bad state, but to make the bad state impossible.
  Eg: if an exception happens because of a input string argument is empty, assert non-emptiness of the argument,
  do not use `if` to tolerate empty input argument, or redefine the argument as `StrEnum`.
- If the bug is caused by exceptional situation, do not handle that, just leave a NOTE of how that exceptional
  situation comes into being.
