from shop.search import Product, search

PRODUCTS = [
    Product("running shoes", 8900, True),
    Product("rain jacket", 12000, False),
    Product("running socks", 1200, True),
]


def test_F011_a_an_exact_name_comes_first():
    assert search(PRODUCTS, "running shoes")[0].name == "running shoes"


def test_F011_b_one_wrong_letter_still_finds_it():
    assert search(PRODUCTS, "runing shoes")[0].name == "running shoes"


def test_F011_c_every_result_has_its_price_and_stock():
    assert all(isinstance(p.price, int) and isinstance(p.in_stock, bool) for p in search(PRODUCTS, "rain jacket"))
