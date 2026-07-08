# Pick next task by examining GitHub issues and kickoff execution

- Enumerate Epic GitHub issues in descending order of priority
- Ask user to pick an Epic to work on
- Pick 1 sub-issue from the Epic and ask for user to confirm
- Call cursor command `/design` to get the high-level design
- Call cursor command `/review_design` to fix the high-level design
- Call cursor command `/plan` to get the detailed implementation plan
- Call cursor command `/review_plan` to fix the implementation plan
- Ask user to kickstart the execution of the plan
