"""Parse checks for the Rise Jane catalog payload."""

import unittest

from dispensary.rise import RiseDispensary, VariantDetails

VAPE_SAMPLE = {
    'product_id': 2034260,
    'brand': 'Double Bear',
    'kind': 'vape',
    'name': 'Royal Durban [2000mg]',
    'brand_subtype': 'Distillate Disposable Pen',
    'category': 'sativa',
    'amount': '2000mg',
    'price_two_gram': 80,
    'special_price_each': {},
    'special_price_gram': {},
    'special_price_half_gram': {},
    'special_price_two_gram': {
        'price': '80.0',
        'discount_type': 'percent',
        'discount_price': '60.0',
        'discount_amount': 20.0,
        'discount_percent': '25.0',
    },
    'special_title': '25% off - Storewide!',
    'lab_results': [
        {
            'price_id': 'gram',
            'lab_results': [
                {'unit': '%', 'value': 86.6, 'unit_id': 'THC', 'compound_name': 'THC'},
                {
                    'unit': '%',
                    'value': 0.4,
                    'unit_id': 'Caryophyllene',
                    'compound_name': 'Caryophyllene',
                },
            ],
        },
    ],
    'store_notes': 'Caryophyllene: 0.209%',
}


class RiseJanePayloadTest(unittest.TestCase):
    def test_empty_special_dicts_parse_as_none(self) -> None:
        item = VariantDetails.model_validate(VAPE_SAMPLE)
        assert item.special_price_gram is None
        assert item.special_price_each is None
        assert item.special_price_two_gram is not None
        assert item.special_price_two_gram.discount_price == '60.0'

    def test_prepare_row_uses_sale_and_fallback_labs(self) -> None:
        dispensary = RiseDispensary.__new__(RiseDispensary)
        item = VariantDetails.model_validate(VAPE_SAMPLE)
        row = dispensary.prepare_row(item, 'two_gram', 'two_gram')
        assert row.full_price == 80.0
        assert row.sale_price == 60.0
        assert row.sale_type == '25.0% off'
        assert row.cannabinoids['THC'] == 0.866
        assert row.terpenes['Caryophyllene'] == 0.004


if __name__ == '__main__':
    unittest.main()
