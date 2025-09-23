import logging

import requests

from dispensary import Dispensary, Product


class RiseDispensary(Dispensary):
    def __init__(self, location_name: str, store_id: int) -> None:
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
                result = response.json()

                total_pages = result['dataSourcePayload']['algolia_total_page']
                inventory_url.query_items['page'] += 1  # type: ignore[operator]

                for variant in result['dataSourcePayload']['algolia']:
                    for item_key in list(variant['variants_details']):
                        item = variant['variants_details'][item_key]
                        logger.info('Processing item %s / %s', item_key, item['name'])

                        for weight_name, price_name, spec_price_name in \
                                [('gram', 'price_gram', 'special_price_gram'),
                                 ('half_gram', 'price_half_gram', 'special_price_half_gram'),
                                 ('two_gram', 'price_two_gram', 'special_price_two_gram')]:

                            if item[price_name]:
                                row = Product(id=item['product_id'],
                                              brand=item['brand'],
                                              type=item['kind'],
                                              subtype=item['brand_subtype'],
                                              strain=item['name'],
                                              strain_type=item['category'],
                                              product_name=' - '.join([item['name'],
                                                                       item['brand_subtype']]),
                                              weight=weight_name,
                                              inventory=None,
                                              full_price=float(item[price_name]),
                                              sale_price=None,
                                              sale_type=None,
                                              sale_description=item['special_title'],
                                              cannabinoids={y['compound_name']:
                                                                float(y['value']) / 100
                                                            for x in item['lab_results']
                                                            if x['price_id'] == weight_name
                                                            for y in x['lab_results']
                                                            if self.is_cannabinoid(
                                                          y['compound_name'])},
                                              terpenes={y['compound_name']: float(y['value']) / 100
                                                        for x in item['lab_results']
                                                        if x['price_id'] == weight_name
                                                        for y in x['lab_results']
                                                        if not self.is_cannabinoid(
                                                          y['compound_name'])},
                                              notes=item['store_notes'])

                                if item[spec_price_name]:
                                    row.sale_price = float(item[spec_price_name]['discount_price'])
                                    if item[spec_price_name]['discount_type'] == 'percent':
                                        row.sale_type = \
                                            f"{item[spec_price_name]['discount_percent']}% off"
                                    elif item[spec_price_name]['discount_type'] == 'target_price':
                                        row.sale_type = \
                                            f"${item[spec_price_name]['discount_price']} sale"

                                self.inventory.append(row)

        self.process_dataframe()
