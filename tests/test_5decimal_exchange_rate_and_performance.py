"""Tests verifying 5-decimal exchange rate precision and performance optimizations."""
import pytest
from decimal import Decimal
from managers.profit_manager import compute_line_tax_and_net
from managers.fx_manager import set_rate, get_rate, convert, calculate_fx_gain_loss, clear_fx_cache
from managers.master_data_crud_manager import list_parties, list_ports, clear_master_data_cache
from managers.rate_master_manager import list_rate_cards
from managers.charge_master_manager import list_charges, list_charge_categories, clear_charges_cache


def test_5decimal_compute_line_tax_and_net():
    """Verify that 5-decimal exchange rate is calculated with accurate Decimal math."""
    # 100 USD @ 35.12345 rate
    qty = 2.0
    unit_price = 50.0  # 100 USD total
    ex_rate = 35.12345
    
    res = compute_line_tax_and_net(
        qty=qty,
        unit_price=unit_price,
        tax_type="VAT 7%",
        wht_type="WHT 3%",
        currency="USD",
        exchange_rate=ex_rate,
    )
    
    assert res["amount"] == 100.00
    assert res["exchange_rate"] == 35.12345
    # 100.00 * 35.12345 = 3512.345 -> 3512.35 THB
    assert res["amount_thb"] == 3512.35
    # Net in USD = 100 + 7 - 3 = 104.00 USD
    assert res["net_amount"] == 104.00
    # Net in THB = 104.00 * 35.12345 = 3652.8388 -> 3652.84 THB
    assert res["net_thb"] == 3652.84


def test_5decimal_fx_manager():
    """Verify fx_manager sets and returns 5-decimal rates accurately."""
    clear_fx_cache()
    test_rate = 35.67891
    set_rate("USD", test_rate)
    
    retrieved = get_rate("USD")
    assert retrieved == 35.67891
    
    # Test convert
    # 1000 USD -> 1000 * 35.67891 = 35678.91 THB
    thb_val = convert(1000, "USD", "THB")
    assert thb_val == 35678.91
    
    # Test FX Gain/Loss calculation with 5 decimals
    fx_res = calculate_fx_gain_loss(
        billed_amount_foreign=1000.0,
        booking_fx_rate=35.12345,
        settlement_fx_rate=35.67891,
        currency="USD"
    )
    assert fx_res["billed_thb"] == 35123.45
    assert fx_res["settled_thb"] == 35678.91
    assert fx_res["fx_gain_loss_thb"] == 555.46
    assert fx_res["status"] == "GAIN"


def test_master_data_batch_fetching_and_cache():
    """Verify batch fetching and caching in list_parties and list_ports."""
    clear_master_data_cache()
    parties = list_parties(active_only=False)
    assert isinstance(parties, list)
    
    # Subsequent call hits cache
    parties_cached = list_parties(active_only=False)
    assert len(parties) == len(parties_cached)
    
    ports = list_ports(active_only=False)
    assert isinstance(ports, list)
    ports_cached = list_ports(active_only=False)
    assert len(ports) == len(ports_cached)


def test_rate_master_batch_lines():
    """Verify list_rate_cards loads lines cleanly without N+1 query errors."""
    cards = list_rate_cards(active_only=False)
    assert isinstance(cards, list)
    for c in cards:
        assert "lines" in c
        assert isinstance(c["lines"], list)


def test_charge_master_cache():
    """Verify list_charges and list_charge_categories caching."""
    clear_charges_cache()
    charges = list_charges(active_only=True)
    assert isinstance(charges, list)
    
    cats = list_charge_categories()
    assert isinstance(cats, list)
    assert len(cats) > 0
