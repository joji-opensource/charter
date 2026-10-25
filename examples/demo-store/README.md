# Demo Store

A small online store used to show Dev Charter at work: six features, two promises and two decisions in plain
English in `charter/`, a little code in `shop/` tagged with the features it serves, and tests named after the checks
they prove.

To see it:

```bash
python -m pytest tests --junitxml=reports/junit.xml   # run the tests and write their results
dev-charter report                                     # rebuild LEDGER.xlsx and status.html
dev-charter status
```

Then open `LEDGER.xlsx`. `shop/discounts.py` serves no feature on purpose: the Code map lists it as Unexplained.
