---
id: CARD-001
title: Order status page
serves: ["F-014.a", "F-014.c"]
state: done                   # open | done
---

**Goal** A signed-in customer opens an order and sees its current step and the carrier's expected delivery date;
anyone else is sent to the sign-in page.

## Plan

- `shop/orders.py`: `order_status(order, viewer)` returns the step and the carrier's date (DEC-001), and refuses
  anyone who is not the order's customer.
- `tests/test_orders.py`: `test_F014_a_order_shows_its_step_and_expected_date`,
  `test_F014_c_someone_elses_order_asks_to_sign_in`.

## Done when

- Both tests pass, and the order page shows the step and date for a real staging order on a phone.

## Allowed paths

- shop/orders.py
- tests/test_orders.py

## Blockers

<!-- Changes outside this card that passed the blocker test (dev-charter guide build): date · file · why -->

## Handoff

- Done, with evidence: the order page shows the step and the carrier's date, and sends anyone else to sign in;
  `test_F014_a_order_shows_its_step_and_expected_date` and `test_F014_c_someone_elses_order_asks_to_sign_in` pass.
- In progress: nothing.
- Parked: showing the courier's location on a map (ideas.md).
- Next step: ask Joji to watch a real staging order end to end and, if it works, sign F-014 off as proven.
