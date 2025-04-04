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

dispensaries = [

    RiseDispensary("Monroeville",
                   2266),

    EthosDispensary("Harmarville",
                    "621900cebbc5580e15476deb",
                    "harmarville.ethoscannabis.com"),

    ZenleafDispensary("Monroeville",
                      "146"),

]

Dispensary.write_spreadsheet(dispensaries, 'leaf_tab.xlsx')

logger.info('Done.')
