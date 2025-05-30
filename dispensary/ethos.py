import concurrent.futures
import json
import logging
import re
from typing import Optional
from urllib.parse import quote
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter

from dispensary import Dispensary
from dispensary import Product

MAX_THREADS = 15
MAX_POOL_SIZE = 30


class EthosDispensary(Dispensary):
    class URLBuilder(Dispensary.URLBuilder):
        @property
        def query(self) -> str:
            return urlencode({x: json.dumps(self.query_items[x], separators=(',', ':'))
            if isinstance(self.query_items[x], dict) else self.query_items[x]
                              for x in self.query_items}, quote_via=quote)

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

    def __init__(self, location_name: str, dispensary_id: str, api_hostname: str):
        super().__init__()
        self.name = f'Ethos {location_name}'
        logger = logging.getLogger(self.name)

        logger.info('Creating Dispensary')
        with requests.Session() as session:
            adapter = HTTPAdapter(pool_connections=MAX_POOL_SIZE, pool_maxsize=MAX_POOL_SIZE)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            session.headers.update({"Content-Type": "application/json"})

            # Get product catalog to get each product cName.
            total_pages = 1
            products_url = self.URLBuilder(
                    netloc=api_hostname,
                    path="/api-4/graphql",
                    query_items={
                        "operationName": "FilteredProducts",
                        "variables": {
                            "includeEnterpriseSpecials": False,
                            "includeCannabinoids": False,
                            "productsFilter": {
                                "productIds": [],
                                "dispensaryId": dispensary_id,
                                "pricingType": "med",
                                "strainTypes": [],
                                "subcategories": [],
                                "Status": "Active",
                                "types": ["Vaporizers"],
                                "useCache": False,
                                "isDefaultSort": True,
                                "sortBy": "weight",
                                "sortDirection": 1,
                                "bypassOnlineThresholds": False,
                                "isKioskMenu": False,
                                "removeProductsBelowOptionThresholds": True,
                            },
                            "page": 0,
                            "perPage": 50,
                        },
                        "extensions": {
                            "persistedQuery": {
                                "version": 1,
                                "sha256Hash": "4bfbf7d757b39f1bed921eab15fc7328dab55a30ad47ff8d5cc499f810ff2aee",
                            }
                        },
                    },
            )
            product_data = []
            while products_url.query_items["variables"]["page"] <= total_pages:  # type: ignore
                logger.info('Reading inventory page %d',
                            products_url.query_items["variables"]["page"])  # type: ignore
                response = session.get(url=products_url.url)
                payload = response.json()

                total_pages = payload['data']['filteredProducts']['queryInfo']['totalPages']
                products_url.query_items["variables"]["page"] += 1  # type: ignore

                product_data.extend(payload["data"]["filteredProducts"]["products"])

            # Get full product details including Cannabinoids and Terpenes
            def get_product_by_cname(product_cname: str) -> Optional[Product]:
                logger.info('Reading full information for %s',
                            product_cname)
                product_url = self.URLBuilder(
                        netloc=api_hostname,
                        path="/api-4/graphql",
                        query_items={
                            "operationName": "IndividualFilteredProduct",
                            "variables": {
                                "includeTerpenes": True,
                                "includeEnterpriseSpecials": False,
                                "includeCannabinoids": True,
                                "productsFilter": {
                                    "cName": product_cname,
                                    "dispensaryId": dispensary_id,
                                    "removeProductsBelowOptionThresholds": False,
                                    "isKioskMenu": False,
                                    "bypassKioskThresholds": False,
                                    "bypassOnlineThresholds": True,
                                    "Status": "All",
                                },
                            },
                            "extensions": {
                                "persistedQuery": {
                                    "version": 1,
                                    "sha256Hash": "48e21bfc45af395e20566dac81472cabb6e0bcf0b0b8cf6ddde10ab6062e3895",
                                }
                            },
                        },
                )
                response = session.get(url=product_url.url)
                payload = response.json()
                if not payload["data"]["filteredProducts"]["products"]:
                    return None
                item = payload["data"]["filteredProducts"]["products"][0]

                product = Product(id=item['id'],
                                  brand=item['brandName'],
                                  type=item['type'],
                                  subtype=item['Name'].split('|')[1].strip(),
                                  strain=item['Name'].split('|')[0].strip(),
                                  strain_type=item['strainType'],
                                  product_name=item['Name'],
                                  weight=self.weight(item['Options'][0]) if item['Options'] else "",
                                  inventory=item['manualInventory'][0]['inventory'],
                                  full_price=item['Prices'][0] if item['Prices'] else 0.0,
                                  sale_price=None,
                                  sale_type=None,
                                  sale_description=None,
                                  cannabinoids={
                                      x['cannabinoid']['name'].split(' ')[0]: float(x['value']) / 100.0 if x[
                                          'value'] else 0
                                      for x in item['cannabinoidsV2']
                                      if not x['cannabinoid']['name'].startswith('"TAC"')},
                                  terpenes={x['libraryTerpene']['name']: float(x['value']) / 100.0 if x['value'] else 0
                                            for x in item['terpenes']},
                                  notes=item['description'])

                if not product.weight and item['manualInventory']:
                    product.weight = self.weight(item['manualInventory'][0]['option'])

                if item['recSpecialPrices']:
                    product.sale_price = item['recSpecialPrices'][0]
                if item['medicalSpecialPrices']:
                    product.sale_price = item['medicalSpecialPrices'][0]

                if item['specialData']:
                    for x in item['specialData']:
                        if not x.startswith('_') and item['specialData'][x]:
                            for y in item['specialData'][x]:
                                product.sale_description = y['specialName']

                return product

            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                product_futures = [executor.submit(get_product_by_cname, cname)
                                   for cname in [x['cName'] for x in product_data]]

                for future in concurrent.futures.as_completed(product_futures):
                    result = future.result()
                    if result:
                        self.inventory.append(result)

        self.process_dataframe()
