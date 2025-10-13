"""Rise Dispensary Location class module."""
import logging

import requests
from pydantic import BaseModel

from dispensary import Dispensary, Product


class VariantBase(BaseModel):
    product_id: int


class VariantInfo(VariantBase):
    amount: str | None


class VariantLabResultDetails(BaseModel):
    unit: str
    value: float
    unit_id: str
    compound_name: str


class VariantLabResults(BaseModel):
    price_id: str
    lab_results: list[VariantLabResultDetails]


class VariantSpecialPrice(BaseModel):
    price: str
    discount_type: str
    discount_price: str
    discount_amount: float
    discount_percent: str


class VariantDetails(VariantBase):
    store_notes: str
    strain: str | None
    aggregate_rating: float
    available_weights: list[str]
    brand: str
    bucket_price: float
    kind_subtype: str
    kind: str
    custom_product_type: str
    root_subtype: str
    special_title: str | None
    lab_results: list[VariantLabResults]
    name: str
    description: str
    category: str | None
    brand_subtype: str
    price_gram: float | None
    price_two_gram: float | None
    price_half_gram: float | None
    special_price_gram: VariantSpecialPrice | None
    special_price_two_gram: VariantSpecialPrice | None
    special_price_half_gram: VariantSpecialPrice | None


class RiseProduct(BaseModel):
    variants: dict[str, VariantInfo]
    variants_details: dict[str, VariantDetails]


class ResultData(BaseModel):
    algolia: list[RiseProduct]
    algolia_page: int
    algolia_total: int
    algolia_total_page: int


class Result(BaseModel):
    dataSourcePayload: ResultData


class RiseDispensary(Dispensary):
    """Rise Dispensary Location class."""

    def __init__(self, location_name: str, store_id: int) -> None:
        """Construct Rise Dispensary object."""
        super().__init__()
        self.name = f'Rise {location_name}'
        logger = logging.getLogger(self.name)

        logger.info('Creating Dispensary')
        with requests.Session() as session:

            total_pages = 1
            inventory_url = self.URLBuilder(netloc='riseheadless-gtiv2.frontastic.live',
                                            path='/frontastic/action/product/pagination',
                                            query_items={'refinementList[root_types][]': 'vape',
                                                         'page': 0,
                                                         'storeId': store_id,
                                                         'stateSlug': '/dispensaries/pennsylvania'})

            while inventory_url.query_items['page'] <= total_pages:  # type: ignore[operator]
                logger.info('Reading inventory page %d', inventory_url.query_items['page'])
                response = session.get(url=inventory_url.url)
                result = Result.model_validate_json(response.text)

                total_pages = result.dataSourcePayload.algolia_total_page
                inventory_url.query_items['page'] += 1  # type: ignore[operator]

                for variant in result.dataSourcePayload.algolia:
                    for item_key, item in variant.variants_details.items():
                        logger.info('Processing item %s / %s', item_key, item.name)

                        for weight_name, price_name, special_price_name in \
                                [('gram', 'price_gram', 'special_price_gram'),
                                 ('half_gram', 'price_half_gram', 'special_price_half_gram'),
                                 ('two_gram', 'price_two_gram', 'special_price_two_gram')]:
                            if getattr(item, price_name):
                                row = Product(id=str(item.product_id),
                                              brand=item.brand,
                                              type=item.kind,
                                              subtype=item.brand_subtype,
                                              strain=item.name,
                                              strain_type=item.category if item.category else "",
                                              product_name=" - ".join([item.name, item.brand_subtype]),
                                              weight=weight_name,
                                              inventory=None,
                                              full_price=float(getattr(item, price_name)),
                                              sale_price=None,
                                              sale_type=None,
                                              sale_description=item.special_title,
                                              cannabinoids={y.compound_name: y.value / 100.0
                                                            for x in item.lab_results if x.price_id == weight_name
                                                            for y in x.lab_results
                                                            if self.is_cannabinoid(y.compound_name)},
                                              terpenes={y.compound_name: y.value / 100
                                                        for x in item.lab_results if x.price_id == weight_name
                                                        for y in x.lab_results
                                                        if not self.is_cannabinoid(y.compound_name)},
                                              notes=item.store_notes)

                                special_price = getattr(item, special_price_name)
                                if special_price:
                                    row.sale_price = special_price.discount_price
                                    if special_price.discount_type == 'percent':
                                        row.sale_type = f"{special_price.discount_percent}% off"
                                    elif special_price.discount_type == 'target_price':
                                        row.sale_type = f"${special_price.discount_price} sale"

                                self.inventory.append(row)

        self.process_dataframe()
