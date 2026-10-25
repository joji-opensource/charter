---
id: F-013
title: Pay with a saved card
area: Checkout
priority: Must
release: Spring launch
state: live
decisions: [DEC-002]
---

**As a** customer
**I want to** pay with a card I saved before, in one tap
**With** the last four digits of the card and the total shown before I confirm
**Must also** never store the full card number ourselves
**So that** buying again takes seconds

## Done means

- **a.** A saved card can be chosen at checkout
- **b.** The total is shown before the customer confirms the payment
- **c.** The full card number never reaches our own database

## Sign-offs

- 2026-10-12 · a · Maya Patel · paid for a real order with a saved card on staging
- 2026-10-12 · b · Maya Patel · saw the total on the confirm screen before paying
- 2026-10-13 · c · Sam Okafor · confirmed with the payment provider's dashboard that only a token is stored
- 2026-10-14 · proven · Maya Patel · ran the whole checkout on a phone and a laptop before launch
