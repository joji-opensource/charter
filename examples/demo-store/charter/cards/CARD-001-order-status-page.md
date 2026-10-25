---
id: CARD-001
title: Order status page
serves: ["F-014.a", "F-014.c"]
state: open                   # open | done
---

**Goal** A signed-in customer opens an order and sees its current step and the carrier's expected delivery date;
anyone else is sent to the sign-in page.

## Plan

- `orders/status.py`: new `order_status(order_id, customer)` returns the step and the carrier's date (DEC-001).
- `orders/views.py`: the order page shows both; it refuses any order that is not the signed-in customer's.
- `tests/test_order_status.py`: `test_F014_a_shows_step_and_date`, `test_F014_c_other_customers_order_signs_in`.

## Done when

- Both tests pass, and the order page shows the step and date for a real staging order on a phone.

## Blockers

<!-- Changes outside this card that passed the blocker test (dev-charter guide build): date · file · why -->
