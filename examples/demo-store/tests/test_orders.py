from datetime import date

import pytest

from shop.orders import Order, SignInRequired, order_status

ORDER = Order(id="A-1001", customer="maya@example.com", step="shipped", carrier_date=date(2026, 10, 28))


def test_F014_a_order_shows_its_step_and_expected_date():
    assert order_status(ORDER, "maya@example.com") == {"step": "shipped", "expected": "2026-10-28"}


def test_F014_c_someone_elses_order_asks_to_sign_in():
    with pytest.raises(SignInRequired):
        order_status(ORDER, "sam@example.com")


def test_P001_a_another_customers_order_is_never_shown():
    with pytest.raises(SignInRequired):
        order_status(ORDER, None)
