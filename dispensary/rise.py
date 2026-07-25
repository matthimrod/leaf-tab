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
    price: float
    discount_type: str
    discount_price: str | None
    discount_amount: float | None
    discount_percent: str | None


class VariantDetails(VariantBase):
    store_notes: str | None
    strain: str | None
    aggregate_rating: float | None
    available_weights: list[str]
    brand: str
    bucket_price: float
    kind_subtype: str
    kind: str
    custom_product_type: str | None
    root_subtype: str | None
    special_title: str | None
    lab_results: list[VariantLabResults]
    name: str
    description: str
    category: str | None
    brand_subtype: str
    price_gram: float | None
    price_two_gram: float | None
    price_half_gram: float | None
    price_each: float | None
    special_price_gram: VariantSpecialPrice | None
    special_price_two_gram: VariantSpecialPrice | None
    special_price_half_gram: VariantSpecialPrice | None
    special_price_each: VariantSpecialPrice | None


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

    def prepare_row(self, item: VariantDetails, weight: str, amount: str | None) -> Product:
        if not amount:
            amount = weight
        special_price = getattr(item, f'special_price_{weight}')
        sale_price, sale_type = None, None
        if special_price:
            sale_price = float(special_price.discount_price)
            if special_price.discount_type == 'percent':
                sale_type = f'{special_price.discount_percent}% off'
            elif special_price.discount_type == 'target_price':
                sale_type = f'${special_price.discount_price} sale'

        return Product(
            id=str(item.product_id),
            brand=item.brand,
            type=item.kind,
            subtype=item.brand_subtype,
            strain=item.name,
            strain_type=item.category or '',
            product_name=f'{item.name} - {item.brand_subtype}',
            weight=amount,
            inventory=None,
            full_price=float(getattr(item, f'price_{weight}')),
            sale_price=sale_price,
            sale_type=sale_type,
            sale_description=item.special_title,
            cannabinoids={
                y.compound_name: y.value / 100.0
                for x in item.lab_results
                if x.price_id == weight
                for y in x.lab_results
                if self.is_cannabinoid(y.compound_name)
            },
            terpenes={
                y.compound_name: y.value / 100
                for x in item.lab_results
                if x.price_id == weight
                for y in x.lab_results
                if not self.is_cannabinoid(y.compound_name)
            },
            notes=item.store_notes or '',
        )

    def __init__(self, location_name: str, store_id: int) -> None:
        """Construct Rise Dispensary object."""
        super().__init__()
        self.name = f'Rise {location_name}'
        logger = logging.getLogger(self.name)

        logger.info('Creating Dispensary')
        with requests.Session() as session:
            total_pages = 1
            inventory_url = self.URLBuilder(
                netloc='riseheadless-gtiv2.frontastic.live',
                path='/frontastic/action/product/pagination',
                query_items={
                    'refinementList[root_types][]': 'vape',
                    'page': 0,
                    'storeId': store_id,
                    'stateSlug': '/dispensaries/pennsylvania',
                },
            )

            while inventory_url.query_items['page'] <= total_pages:  # type: ignore[operator]
                logger.info('Reading inventory page %d', inventory_url.query_items['page'])
                response = session.get(url=inventory_url.url)
                result = Result.model_validate_json(response.text)

                total_pages = result.dataSourcePayload.algolia_total_page
                inventory_url.query_items['page'] += 1  # type: ignore[operator]

                for variant in result.dataSourcePayload.algolia:
                    for item_key, item in variant.variants_details.items():
                        logger.info('Processing item %s / %s', item_key, item.name)

                        for weight in ['gram', 'half_gram', 'two_gram']:
                            if getattr(item, f'price_{weight}'):
                                self.inventory.append(
                                    self.prepare_row(item, weight, weight),
                                )

            total_pages = 1
            inventory_url = self.URLBuilder(
                netloc='riseheadless-gtiv2.frontastic.live',
                path='/frontastic/action/product/pagination',
                query_items={
                    'refinementList[root_types][]': 'edible',
                    'page': 0,
                    'storeId': store_id,
                    'stateSlug': '/dispensaries/pennsylvania',
                },
            )

            while inventory_url.query_items['page'] <= total_pages:  # type: ignore[operator]
                logger.info('Reading inventory page %d', inventory_url.query_items['page'])
                response = session.get(url=inventory_url.url)
                result = Result.model_validate_json(response.text)

                total_pages = result.dataSourcePayload.algolia_total_page
                inventory_url.query_items['page'] += 1  # type: ignore[operator]

                for variant in result.dataSourcePayload.algolia:
                    for item_key, item in variant.variants_details.items():
                        logger.info('Processing item %s / %s', item_key, item.name)

                        weight = 'each'
                        amount = variant.variants[weight].amount
                        if getattr(item, f'price_{weight}'):
                            self.inventory.append(self.prepare_row(item, weight, amount))

        self.process_dataframe()
