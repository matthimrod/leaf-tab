"""LeafTab: The Cannalyzer."""

import argparse
import logging
import sys

from dispensary import Dispensary
from dispensary.ethos import EthosDispensary
from dispensary.rise import RiseDispensary
from dispensary.zenleaf import ZenleafDispensary

logging.basicConfig(handlers=[logging.StreamHandler(sys.stdout)],
                    encoding='utf-8',
                    level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger('LeafTab')

logger.info('Starting.')

parser = argparse.ArgumentParser(prog='leaf_tab',
                                 description='Leaf Tab: The Cannalyzer. '
                                             'A dispensary data gathering utility.')
parser.add_argument('-o', '--output',
                    help='Output spreadsheet filename.',
                    default='leaf_tab.xlsx')
args = parser.parse_args()

dispensaries: list[Dispensary] = [

    RiseDispensary('Monroeville',
                   2266),

    EthosDispensary('Harmarville',
                    '621900cebbc5580e15476deb',
                    'harmarville.ethoscannabis.com'),

    ZenleafDispensary('Monroeville',
                      '146'),

]

Dispensary.write_spreadsheet(dispensaries, args.output)

logger.info('Done.')
