import pytest

from shop.payments import PriceChanged, SavedCard, charge, confirm_screen

CARD = SavedCard(token="tok_4f9a", last_four="4242")


def test_F013_a_a_saved_card_can_be_chosen():
    assert CARD.label() == "Card ending 4242"


def test_F013_b_the_total_is_shown_before_paying():
    assert confirm_screen(CARD, 2599) == "Pay 25.99 with Card ending 4242"


def test_F013_c_only_the_token_is_kept():
    assert charge(CARD, 2599, 2599) == {"token": "tok_4f9a", "amount": 2599}


def test_P002_a_the_amount_charged_is_the_total_shown():
    assert charge(CARD, 2599, 2599)["amount"] == 2599


def test_P002_b_a_changed_price_is_confirmed_before_paying():
    with pytest.raises(PriceChanged):
        charge(CARD, 2599, 2799)
