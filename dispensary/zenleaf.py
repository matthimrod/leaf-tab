import concurrent.futures
import logging
import math
import re

import requests
from requests.adapters import HTTPAdapter

from dispensary import Dispensary
from dispensary import Product

MAX_THREADS = 15
MAX_POOL_SIZE = 30


class ZenleafDispensary(Dispensary):
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

    def __init__(self, location_name: str, store_id: str):
        super().__init__()
        self.name = f'Zenleaf {location_name}'
        logger = logging.getLogger(self.name)

        logger.info('Creating Dispensary')
        with requests.Session() as session:
            adapter = HTTPAdapter(pool_connections=MAX_POOL_SIZE, pool_maxsize=MAX_POOL_SIZE)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            session.headers.update({'Storeid': store_id})

            # Get product catalog to get each product
            total_pages = 1
            request_body = {
                'filters': {'category': [140932]},
                'page': 1,
                'pageSize': 24,
                'sortingMethodId': 7,
                'searchTerm': '',
                'platformOs': 'web'
            }
            product_data = []
            while request_body['page'] <= total_pages:  # type: ignore
                logger.info('Reading inventory page %d', request_body['page'])

                response = session.post(url='https://sweed.app/_api/proxy/Products/GetProductList',
                                        json=request_body)
                payload = response.json()

                total_pages = math.ceil(payload['total'] / payload['pageSize'])
                request_body['page'] += 1  # type: ignore

                product_data.extend(payload['list'])

            def get_product_by_id(variant_id: str) -> Product:
                logger.info('Reading full information for %s', variant_id)
                product_response = session.post(url='https://sweed.app/_api/proxy/Products/GetProductByVariantId',
                                                json={"variantId": variant_id, "platformOs": "web"})
                item = product_response.json()

                lab_response = session.post(url='https://sweed.app/_api/proxy/Products/GetExtendedLabdata',
                                            json={"variantId": variant_id, "platformOs": "web"})
                lab_payload = lab_response.json()

                return Product(id=item['id'],
                               brand=item['brand']['name'],
                               type=item['category']['name'],
                               subtype=item['subcategory']['name'],
                               strain=item['strain']['name'],
                               strain_type=item['strain']['prevalence']['name'],
                               product_name=" - ".join([item['name'], item['variants'][0]['name']]),
                               weight=self.weight(item['variants'][0]['name']),
                               inventory=item['variants'][0]['availableQty'],
                               full_price=item['variants'][0]['price'],
                               sale_price=item['variants'][0]['promoPrice'],
                               sale_type=None,
                               sale_description=' & '.join([promo['name'] for promo in item['variants'][0]['promos']]),
                               cannabinoids={x['name']: float(x['min'] / 100.0)
                                             for x in lab_payload['thc']['values']
                                             if not x['name'].startswith('Total')} |
                                            {x['name']: float(x['min'] / 100.0)
                                             for x in lab_payload['cbd']['values']
                                             if not x['name'].startswith('Total')},
                               terpenes={x['name']: float(x['min'] / 100.0)
                                         for x in lab_payload['terpenes']['values']
                                         if not x['name'].startswith('Total')},
                               notes=item['description'])

            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                product_futures = [executor.submit(get_product_by_id, variant_id)
                                   for variant_id in [item['id'] for sublist in
                                                      [x['variants'] for x in product_data]
                                                      for item in sublist]]
                for future in concurrent.futures.as_completed(product_futures):
                    self.inventory.append(future.result())

        self.process_dataframe()
