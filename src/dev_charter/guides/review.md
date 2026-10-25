# Review: two passes over the plan, problems first

Review the plan twice before probing or building. Lead with what is wrong; the point is to fix the right thing.

## Walk this list literally

For each line, write the finding or "none found". Skip nothing.

**Bugs**
- Where does it break on the first real input that is not the happy path?
- What does it assume exists that nothing in the plan creates?
- At each step, what happens on failure, and would anyone see it?
- Does it rely on an order of steps that nothing enforces?

**Missing detail**
- Which file, function or contract is named vaguely?
- Which change has no way of being verified?
- Which check on the card has no change serving it, and which change serves no check?

**Over-engineering**
- Is anything built from scratch where something proven already exists?
- Is there a second way of doing what one path already does?
- Is anything built for a case that is not on the card?
- Is there a special case where a general rule would do?
- Is there a setting, switch or abstraction "for flexibility" that nobody needs today?

**Inconsistency**
- Does the plan contradict itself?
- Does it describe names, files or behaviour that do not match the code as it is?
- Does it disagree with the features, promises or decisions in `charter/`? Different words for the same thing count.

**Generality**
- Is any customer name, organisation or identifier written into the code?
- Does it assume one vendor, one environment or one shape of data where the product supports several?

## Two passes

Fix the plan after the first pass, then walk the list again from the top. The second pass should find fewer and
smaller problems. If it still finds a structural one (a missing part, a wrong boundary, a contract that cannot
hold), fix it and go again. Stop when what remains is no longer structural.

## What to hand over

The problems, each with its fix; the updated plan; and the load-bearing assumptions for `dev-charter guide probe`.
