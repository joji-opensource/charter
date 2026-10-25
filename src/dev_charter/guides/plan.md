# Plan: a file-level plan the person approves before any code

1. **Name what the work serves**: the feature and the Done-means checks, such as `F-014.a` and `F-014.c`. If nothing
   fits, stop: propose a feature (`dev-charter guide feature`) or park the idea.
2. **Make a task card**: `dev-charter card new "<title>" --serves F-014.a --serves F-014.c`. The plan goes in the
   card. One card at a time.
3. **Write a plan that names real things:**
   - the exact files to create, change or remove;
   - the contracts that change (function signatures, data shapes, commands, screens, messages) and what depends on
     them;
   - what each file gains or loses, specifically: not "update the orders module" but "add the delivery date to
     `order_summary()` and show it on the order page";
   - the assumptions, stated, so the risky ones can be probed (`dev-charter guide probe`);
   - how it will be proven: the tests named after their checks (`test_F014_a_…`) and the end-to-end check;
   - what the person will be able to see or run when it is done.

   A general description is a task list, not a plan.
4. **Size it to the card.** If the plan reaches beyond the checks the card serves, the card or the plan is wrong;
   fix it with the person before building.
5. **Use three lenses at once.** Architect: does something already do this? Extend it. Product: is this the right
   thing, and the simplest way to prove it? User: every extra step, choice or screen is a cost to the person using
   it.
6. **Decide the obvious; bring the consequential** to the person with a recommendation.
7. **Show the plan and wait for a go-ahead.** Silence is not a yes. Then review it (`dev-charter guide review`).
