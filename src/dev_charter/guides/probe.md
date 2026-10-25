# Probe: prove the plan's risky assumptions before building

A review opinion is a guess; a probe result is a fact. Documents do not fail, code does.

1. **List the load-bearing assumptions**: the ones the plan falls apart without. If the plan still works when an
   assumption is false, it is not load-bearing; leave it.
2. **Design a cheap probe for each**: hours, not days. It runs against the real code and the real data or service,
   never a mock of the thing being tested. Write down the assumption, the method, and what result would prove it
   wrong.
3. **Ask before probes that cost money or touch shared systems.** List them with an estimate and wait for the go.
4. **Record each result on the task card**:

   ```
   Probe: <name>
   Assumption: <the exact claim, and where the plan makes it>
   Method: <what ran, against what, how many times>
   Verdict: PASS | PARTIAL | FAIL
   The fact: <what was measured, with numbers>
   What changes: <the correction to the plan, or "nothing">
   ```

5. **Fold the facts in.** A PASS confirms the assumption. A PARTIAL or FAIL is a proven gap: it becomes a change to
   the plan, or a scope question for the person, never a quiet workaround.
6. **Check the fold.** Re-read the part of the plan the probe corrects and confirm the plan itself changed, not just
   a note about it. Every item under "What changes" lands where it says. A fix that changes behaviour is proven by
   running it, not by reading it. Search for the old value: any copy left behind is a contradiction.

Probe code is scratch: keep it out of the product's code. Build starts when every load-bearing assumption has a fact
behind it.
