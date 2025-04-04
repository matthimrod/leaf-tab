import logging
import re
import warnings
from dataclasses import dataclass
from typing import NamedTuple
from typing import Optional
from urllib.parse import urlencode
from urllib.parse import urlunparse

warnings.simplefilter(action='ignore', category=FutureWarning)
import pandas
from pandas import DataFrame


GREEN = '#63BE7B'
WHITE = '#FFFFFF'


@dataclass
class Product:
    id: str                            # Product ID/Primary Key
    brand: str                         # Brand: Double Bear, Organic Remedies, Rythm, etc
    type: str                          # Vape
    subtype: str                       # Live Resin; Live Sauce; Disposable; etc.
    strain: str                        # Strain Name
    strain_type: str                   # Botanical Type: Sativa; Indica; Hybrid
    product_name: str                  # Full product name or concat strain + subtype
    weight: str                        # sub_half; half_gram; gram; two_gram
    inventory: Optional[int]           # On-hand number, if available
    full_price: float
    sale_price: Optional[float]
    sale_type: Optional[str]           # Sale calculation type: %-off, $-off
    sale_description: Optional[str]    # Sale title/description
    cannabinoids: dict[str, float]     # Dict of cannabinoids (THC, CBD)
    terpenes: dict[str, float]         # Dict of terpenes (Myrcene, Linalool, etc)
    notes: str                         # Notes/product description


class Dispensary:
    name: str
    inventory: list[Product]
    inventory_data: DataFrame
    _cannabinoids: set
    _terpenes: set

    def __init__(self):
        self.name = ""
        self.inventory = []
        self.inventory_data = pandas.DataFrame()
        self._cannabinoids = set()
        self._terpenes = set()

    @property
    def cannabinoids(self):
        return [x for x in sorted(self._cannabinoids) if x.startswith('THC')] + \
            [x for x in sorted(self._cannabinoids) if not x.startswith('THC')]

    @property
    def terpenes(self):
        return sorted(self._terpenes)

    def process_dataframe(self):
        for this in self.inventory:
            row = {
                'id': [this.id],
                'brand': [this.brand],
                'type': [this.type],
                'subtype': [this.subtype],
                'strain': [this.strain],
                'strain_type': [this.strain_type],
                'product_name': [this.product_name],
                'weight': [this.weight],
                'inventory': [this.inventory],
                'full_price': [this.full_price],
                'sale_price': [this.sale_price],
                'sale_type': [this.sale_type],
                'sale_description': [this.sale_description]
            }

            for name, value in this.cannabinoids.items():
                self._cannabinoids.add(name)
                row[name] = [value]

            for name, value in this.terpenes.items():
                self._terpenes.add(name)
                row[name] = [value]

            row['notes'] = [this.notes]

            record = DataFrame(row)
            record.dropna(axis=1, how='all')
            self.inventory_data = pandas.concat([self.inventory_data, record])

    class URLBuilder(NamedTuple):
        scheme: str = 'https'
        netloc: str = ''
        path: str = ''
        params: str = ''
        query_items: dict[str, str | int | dict] = {}
        fragment: str = ''

        @property
        def query(self) -> str:
            return urlencode(self.query_items)

        @property
        def url(self) -> str:
            return urlunparse((self.scheme,
                               self.netloc,
                               self.path,
                               self.params,
                               self.query,
                               self.fragment))

    @staticmethod
    def is_cannabinoid(name: str) -> bool:
        """
        Identify a cannabinoid (vs. terpene) by "THC" or "CB*"
        """
        if re.match('THC', name):
            return True
        if re.match('^CB', name):
            return True
        return False

    @staticmethod
    def excel_column_name(n):
        """
        Convert a zero-based index to an Excel-style column name.
        """
        result = ""
        while n >= 0:
            result = chr(n % 26 + 65) + result
            n = n // 26 - 1
        return result

    @staticmethod
    def write_spreadsheet(dispensaries: list["Dispensary"], file_name: str) -> None:
        logger = logging.getLogger('Dispensary Spreadsheet Writer')
        logger.info('Writing spreadsheet %s', file_name)
        with pandas.ExcelWriter(file_name, engine='xlsxwriter') as writer:
            workbook = writer.book
            percent_format = workbook.add_format({'num_format': '0.00%'})
            accounting_format = workbook.add_format(
                    {'num_format': '_($* #,##0.00_);_($* (#,##0.00);_($* "-"??_);_(@_)'})
            category_format = {
                'sativa': workbook.add_format({'font_color': '#FF0000'}),
                'hybrid': workbook.add_format({'font_color': '#008000'}),
                'indica': workbook.add_format({'font_color': '#0000FF'})
            }

            for dispensary in dispensaries:
                column_order = []
                for col in dispensary.inventory_data.columns:
                    if col not in dispensary.terpenes and col not in dispensary.cannabinoids and col != 'notes':
                        column_order.append(col)
                column_order.extend(dispensary.cannabinoids)
                column_order.extend(dispensary.terpenes)
                if 'notes' in dispensary.inventory_data.columns:
                    column_order.append('notes')

                dispensary.inventory_data = dispensary.inventory_data[column_order]

                column_map = {col: Dispensary.excel_column_name(i) for i, col, in
                              enumerate(dispensary.inventory_data.columns.tolist())}

                logger.info('Creating worksheet for %s', dispensary.name)
                dispensary.inventory_data.to_excel(writer, index=False, sheet_name=dispensary.name)
                worksheet = writer.sheets[dispensary.name]

                logger.info('Adding formatting to worksheet %s', dispensary.name)
                for row in range(2, len(dispensary.inventory_data) + 2):
                    strain = dispensary.inventory_data.iloc[row - 2]['strain']
                    product_name = dispensary.inventory_data.iloc[row - 2]['product_name']
                    strain_type = str(dispensary.inventory_data.iloc[row - 2]['strain_type']).lower()
                    if strain_type in category_format:
                        worksheet.write(f"{column_map['strain']}{row}", strain, category_format[strain_type])
                        worksheet.write(f"{column_map['product_name']}{row}", product_name,
                                        category_format[strain_type])

                    worksheet.conditional_format(
                            f'{column_map[dispensary.terpenes[0]]}{row}:{column_map[dispensary.terpenes[-1]]}{row}',
                            {
                                'type': '2_color_scale',
                                'min_color': WHITE,
                                'max_color': GREEN
                            }
                    )

                worksheet.autofilter(0, 0, len(dispensary.inventory_data), len(dispensary.inventory_data.columns))

                # for column in ADJUST_WIDTH_FIELDS:
                for col in dispensary.inventory_data.columns:
                    if col not in dispensary.terpenes and col not in dispensary.cannabinoids and col != 'notes':
                        max_len = max(
                                dispensary.inventory_data[col].astype(str).map(len).max(),
                                # Length of the longest cell in the column
                                len(col)  # Length of the column name
                        ) + 3  # Adding some padding
                        worksheet.set_column(f'{column_map[col]}:{column_map[col]}', max_len)

                for col in [x for x in dispensary.inventory_data.columns if 'price' in x]:
                    worksheet.set_column(f'{column_map[col]}:{column_map[col]}', None, accounting_format)

                for col in dispensary.cannabinoids:
                    worksheet.set_column(f'{column_map[col]}:{column_map[col]}', None, percent_format)
                for col in dispensary.terpenes:
                    worksheet.set_column(f'{column_map[col]}:{column_map[col]}', None, percent_format)
