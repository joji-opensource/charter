# Verify: prove the work on a real run

"Looks done" is not done. A card is done when its **Done when** passes on a real run, the check the person agreed
to, not a different one.

1. **Tests, named after their checks.** Anything that will run again is a real test in the repository, never a
   one-off script that is thrown away.
2. **The real thing, end to end, where a person will see it**: the real screen, the real message, the real request
   through the real interface.
3. **Against real systems** where they are available. If the real system is not available, the work is not
   verified; say so.
4. **Never make a test lie.** No swallowed error, widened tolerance, skipped case or loosened assertion. A flaky test
   is a defect to fix, not a test to rerun until it passes. Expected output changes only when the change means to
   change it, and the commit says so.
5. **Update the record.** Run the tests so they write their results where `charter.toml` expects them, then
   `dev-charter check` and `dev-charter report`.
6. **Leave sign-offs to people.** When a check can only be confirmed by a person (a text arriving on a real phone, a
   page loading fast enough on a real device), say exactly what they should do and look for. They write the
   sign-off.
7. **Report what happened.** Failures with their output; skipped steps with the reason; what passed, plainly.
