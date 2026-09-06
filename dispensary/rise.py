"""Rise Dispensary Location class module."""

from __future__ import annotations

import logging
from typing import ClassVar

import requests
from pydantic import BaseModel, ConfigDict, Field, field_validator

from dispensary import Dispensary, Product

JANE_HOST = 'dmerch.iheartjane.com'
# Public Jane Digital Merchandising key embedded in risecannabis.com.
JANE_API_KEY = '2ac0a083-6233-4b68-b4a6-b0ea26bb5715'
JANE_PAGE_SIZE = 60
VAPE_WEIGHTS = ('gram', 'half_gram', 'two_gram')


class VariantLabResultDetails(BaseModel):
    model_config = ConfigDict(extra='ignore')

    unit: str
    value: float
    unit_id: str
    compound_name: str


class VariantLabResults(BaseModel):
    model_config = ConfigDict(extra='ignore')

    price_id: str
    lab_results: list[VariantLabResultDetails]


class VariantSpecialPrice(BaseModel):
    model_config = ConfigDict(extra='ignore')

    price: float | None = None
    discount_type: str | None = None
    discount_price: str | None = None
    discount_amount: float | None = None
    discount_percent: str | None = None


class VariantDetails(BaseModel):
    model_config = ConfigDict(extra='ignore')

    product_id: int
    store_notes: str | None = None
    strain: str | None = None
    aggregate_rating: float | None = None
    available_weights: list[str] = Field(default_factory=list)
    brand: str
    bucket_price: float | None = None
    kind_subtype: str | None = None
    kind: str
    custom_product_type: str | None = None
    root_subtype: str | None = None
    special_title: str | None = None
    lab_results: list[VariantLabResults] = Field(default_factory=list)
    name: str
    description: str | None = None
    category: str | None = None
    brand_subtype: str = ''
    amount: str | None = None
    price_gram: float | None = None
    price_two_gram: float | None = None
    price_half_gram: float | None = None
    price_each: float | None = None
    special_price_gram: VariantSpecialPrice | None = None
    special_price_two_gram: VariantSpecialPrice | None = None
    special_price_half_gram: VariantSpecialPrice | None = None
    special_price_each: VariantSpecialPrice | None = None

    @field_validator(
        'special_price_gram',
        'special_price_two_gram',
        'special_price_half_gram',
        'special_price_each',
        mode='before',
    )
    @classmethod
    def empty_special_as_none(cls, value: object) -> object:
        if value == {}:
            return None
        return value


class JaneProduct(BaseModel):
    model_config = ConfigDict(extra='ignore')

    object_id: str
    product_id: int | None = None
    search_attributes: VariantDetails | None = None


class JaneSearchResult(BaseModel):
    model_config = ConfigDict(extra='ignore')

    nb_hits: int = 0
    products: list[JaneProduct] = []


class RiseDispensary(Dispensary):
    """Rise Dispensary Location class."""

    _jane_headers: ClassVar[dict[str, str]] = {
        'Accept': 'application/json',
        'Content-Type': 'text/plain',
    }

    def prepare_row(self, item: VariantDetails, weight: str, amount: str | None) -> Product:
        if not amount:
            amount = weight
        special_price = getattr(item, f'special_price_{weight}')
        sale_price, sale_type = None, None
        if special_price and special_price.discount_price:
            sale_price = float(special_price.discount_price)
            if special_price.discount_type == 'percent':
                sale_type = f'{special_price.discount_percent}% off'
            elif special_price.discount_type == 'target_price':
                sale_type = f'${special_price.discount_price} sale'

        lab_groups = [x for x in item.lab_results if x.price_id == weight] or item.lab_results

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
                for x in lab_groups
                for y in x.lab_results
                if self.is_cannabinoid(y.compound_name)
            },
            terpenes={
                y.compound_name: y.value / 100
                for x in lab_groups
                for y in x.lab_results
                if not self.is_cannabinoid(y.compound_name)
            },
            notes=item.store_notes or '',
        )

    def _jane_url(self, path: str) -> str:
        return self.URLBuilder(
            netloc=JANE_HOST,
            path=path,
            query_items={
                'jdm_api_key': JANE_API_KEY,
                'jdm_source': 'sdk',
                'jdm_version': '2.16.0',
            },
        ).url

    def _jane_post(
        self,
        session: requests.Session,
        path: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        response = session.post(
            self._jane_url(path),
            json=payload,
            headers=self._jane_headers,
            timeout=90,
        )
        response.raise_for_status()
        if not response.content:
            return {}
        data = response.json()
        return data if isinstance(data, dict) else {}

    def _fetch_category(
        self,
        session: requests.Session,
        store_id: int,
        root_type: str,
        logger: logging.Logger,
    ) -> list[VariantDetails]:
        logger.info('Reading %s inventory', root_type)
        payload: dict[str, object] = {
            'app_mode': 'headless',
            'jane_device_id': 'leaf-tab',
            'search_attributes': ['*'],
            'store_id': store_id,
            'disable_ads': True,
            'page_size': JANE_PAGE_SIZE,
            'placement': 'menu_inline_table',
            'search_filter': f'root_types:{root_type}',
            'search_query': '',
        }
        result = JaneSearchResult.model_validate(
            self._jane_post(session, '/v2/smart', payload),
        )
        items: list[VariantDetails] = []
        pending_ids: list[str] = []
        for product in result.products:
            if product.search_attributes:
                items.append(product.search_attributes)
            else:
                pending_ids.append(product.object_id)

        logger.info(
            'Hydrating %d of %d %s products',
            len(pending_ids),
            result.nb_hits or len(result.products),
            root_type,
        )
        for offset in range(0, len(pending_ids), JANE_PAGE_SIZE):
            chunk = pending_ids[offset:offset + JANE_PAGE_SIZE]
            logger.info(
                'Reading %s details %d-%d',
                root_type,
                offset,
                offset + len(chunk) - 1,
            )
            page = JaneSearchResult.model_validate(
                self._jane_post(
                    session,
                    '/v2/smartpage',
                    {
                        'app_mode': 'headless',
                        'jane_device_id': 'leaf-tab',
                        'object_ids': chunk,
                        'search_attributes': ['*'],
                        'store_id': store_id,
                    },
                ),
            )
            items.extend(
                product.search_attributes
                for product in page.products
                if product.search_attributes
            )
        return items

    def __init__(self, location_name: str, store_id: int) -> None:
        """Construct Rise Dispensary object."""
        super().__init__()
        self.name = f'Rise {location_name}'
        logger = logging.getLogger(self.name)

        logger.info('Creating Dispensary')
        with requests.Session() as session:
            for item in self._fetch_category(session, store_id, 'vape', logger):
                logger.info('Processing item %s / %s', item.product_id, item.name)
                for weight in VAPE_WEIGHTS:
                    if getattr(item, f'price_{weight}'):
                        self.inventory.append(self.prepare_row(item, weight, weight))

            for item in self._fetch_category(session, store_id, 'edible', logger):
                logger.info('Processing item %s / %s', item.product_id, item.name)
                if item.price_each:
                    self.inventory.append(
                        self.prepare_row(item, 'each', item.amount),
                    )

        self.process_dataframe()
