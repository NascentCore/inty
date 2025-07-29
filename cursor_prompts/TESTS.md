# Instructions for writing tests

* Use `pytest` framework
* PYTHONPATH is set to the root of the git repo, import module accordingly
* Whenever possible, do not use mocks
* Write easy-to-understand assertions
* Write as few assertions as possible
* Unless specifically asked, write tests only for important methods/classes;
  do not write tests for everything.
* Unless specifically asked otherwise, generate 1 happy case test for each test target
* Do not write `main()` function, assume test will be executed by `pytest`, which can discover test targets
