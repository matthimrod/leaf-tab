"""ZenLeaf Dispensary Location class module."""

import concurrent.futures
import logging
import math
import re

import requests
from pydantic import BaseModel
from requests.adapters import HTTPAdapter

from dispensary import Dispensary, Product

MAX_THREADS = 15
MAX_POOL_SIZE = 30


class ZenLeafProductBrand(BaseModel):
    name: str


class ZenLeafProductCategory(BaseModel):
    id: int
    name: str


class ZenLeafProductPrevalence(BaseModel):
    name: str


class ZenLeafProductPromo(BaseModel):
    name: str


class ZenLeafProductStrain(BaseModel):
    name: str
    prevalence: ZenLeafProductPrevalence


class ZenLeafProductResultVariant(BaseModel):
    id: int
    name: str
    availableQty: int | None = None
    price: float
    promoPrice: float | None = None
    promos: list[ZenLeafProductPromo]


class ZenLeafProductResult(BaseModel):
    id: int
    name: str
    category: ZenLeafProductCategory
    subcategory: ZenLeafProductCategory
    brand: ZenLeafProductBrand
    strain: ZenLeafProductStrain | None = None
    variants: list[ZenLeafProductResultVariant]


class ZenLeafProductVariantDetail(ZenLeafProductResult):
    description: str | None = None


class ZenLeafLabDataItem(BaseModel):
    name: str
    code: str
    min: float
    max: float


class ZenLeafLabDataDetail(BaseModel):
    values: list[ZenLeafLabDataItem]


class ZenLeafLabData(BaseModel):
    thc: ZenLeafLabDataDetail
    cbd: ZenLeafLabDataDetail
    terpenes: ZenLeafLabDataDetail


class Result(BaseModel):
    page: int
    pageSize: int
    total: int
    list: list


class ZenleafDispensary(Dispensary):
    """ZenLeaf Dispensary Location class."""

    @staticmethod
    def weight(this: str) -> str:
        if re.match(r'\.[1-4]g', this):
            return 'sub_half'
        if re.match(r'\.5g', this):
            return 'half_gram'
        if re.match(r'1g', this):
            return 'gram'
        if re.match(r'2g', this):
            return 'two_gram'
        return this

    def __init__(self, location_name: str, store_id: str) -> None:
        """Construct ZenLeaf Dispensary object."""
        super().__init__()
        self.name = f'Zenleaf {location_name}'
        logger = logging.getLogger(self.name)

        logger.info('Creating Dispensary')
        with requests.Session() as session:
            adapter = HTTPAdapter(pool_connections=MAX_POOL_SIZE, pool_maxsize=MAX_POOL_SIZE)
            session.mount('https://', adapter)
            session.mount('http://', adapter)
            session.headers.update({'Storeid': store_id})

            # Get product catalog to get each product
            total_pages = 1
            request_body = {
                'filters': {'category': [140932]},
                'page': 1,
                'pageSize': 24,
                'sortingMethodId': 7,
                'searchTerm': '',
                'platformOs': 'web',
            }
            product_data = []
            while request_body['page'] <= total_pages:  # type: ignore[operator]
                logger.info('Reading inventory page %d', request_body['page'])

                response = session.post(url='https://sweed.app/_api/proxy/Products/GetProductList',
                                        json=request_body)
                payload = Result.model_validate_json(response.text)

                total_pages = math.ceil(payload.total / payload.pageSize)
                request_body['page'] += 1  # type: ignore[operator]

                product_data.extend(payload.list)

            def get_product_by_id(variant_id: str) -> Product | None:
                logger.info('Reading full information for %s', variant_id)
                product_response = session.post(url='https://sweed.app/_api/proxy/Products/GetProductByVariantId',
                                                json={"variantId": variant_id, "platformOs": "web"})
                item = ZenLeafProductVariantDetail.model_validate_json(product_response.text)

                lab_response = session.post(url='https://sweed.app/_api/proxy/Products/GetExtendedLabdata',
                                            json={"variantId": variant_id, "platformOs": "web"})
                lab_payload = ZenLeafLabData.model_validate_json(lab_response.text)

                try:
                    return Product(id=str(item.id),
                                   brand=item.brand.name,
                                   type=item.category.name,
                                   subtype=item.subcategory.name,
                                   strain=item.strain.name if item.strain else '',
                                   strain_type=item.strain.prevalence.name if item.strain and item.strain.prevalence else '',
                                   product_name=" - ".join([item.name, item.variants[0].name]),
                                   weight=self.weight(item.variants[0].name),
                                   inventory=item.variants[0].availableQty,
                                   full_price=item.variants[0].price,
                                   sale_price=item.variants[0].promoPrice,
                                   sale_type=None,
                                   sale_description=' & '.join([promo.name for promo in item.variants[0].promos]),
                                   cannabinoids={x.name: x.min / 100.0
                                                 for x in lab_payload.thc.values
                                                 if not x.name.startswith('Total')} |
                                                {x.name: x.min / 100.0
                                                 for x in lab_payload.cbd.values
                                                 if not x.name.startswith('Total')},
                                   terpenes={x.name: x.min / 100.0
                                             for x in lab_payload.terpenes.values
                                             if not x.name.startswith('Total')},
                                   notes=item.description or '')
                except TypeError:
                    return None
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                product_futures = [executor.submit(get_product_by_id, variant_id)
                                   for variant_id in [item['id'] for sublist in
                                                      [x['variants'] for x in product_data]
                                                      for item in sublist]]
                inventory = [future.result()
                             for future in concurrent.futures.as_completed(product_futures)]
                self.inventory = [item for item in inventory if item is not None]

        self.process_dataframe()
