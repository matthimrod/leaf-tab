"""LeafTab: The Cannalyzer."""

import argparse
import logging
import sys
from datetime import datetime
from datetime import timezone
from io import BytesIO

import boto3
from dotenv import load_dotenv

from dispensary import Dispensary
from dispensary.ethos import EthosDispensary
from dispensary.rise import RiseDispensary
from dispensary.zenleaf import ZenleafDispensary

load_dotenv()


def main() -> None:
    """
    Main function
    """
    logging.basicConfig(handlers=[logging.StreamHandler(sys.stdout)],
                        encoding='utf-8',
                        level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(message)s')
    logger = logging.getLogger('LeafTab')

    logger.info('Starting.')

    dispensaries: list[Dispensary] = [

        RiseDispensary('Monroeville',
                       2266),

        EthosDispensary('Harmarville',
                        '621900cebbc5580e15476deb',
                        'harmarville.ethoscannabis.com'),

        ZenleafDispensary('Monroeville',
                          '146'),

    ]

    s3_client = boto3.client('s3')

    for dispensary in dispensaries:
        parquet_file = dispensary.inventory_data.to_parquet()
        s3_client.put_object(Bucket='leaf-tab',
                             Key=f'{datetime.now(timezone.utc).strftime('%Y-%m-%d')}/{dispensary.name}.parquet',
                             Body=parquet_file)

    output = BytesIO()
    Dispensary.write_spreadsheet(dispensaries, output)
    output.seek(0)
    s3_client.put_object(Bucket='leaf-tab',
                         Key=f'{datetime.now(timezone.utc).strftime('%Y-%m-%d')}/leaf-tab.xlsx',
                         Body=output.getvalue())

    logger.info('Done.')


def run():
    parser = argparse.ArgumentParser(prog='leaf_tab',
                                     description='Leaf Tab: The Cannalyzer. '
                                                 'A dispensary data gathering utility.')
    # parser.add_argument('-o', '--output',
    #                     help='Output URL.',
    #                     default='leaf_tab.xlsx')
    args = parser.parse_args()

    main()


if __name__ == '__main__':
    run()
