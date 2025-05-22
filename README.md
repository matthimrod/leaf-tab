# LeafTab: The Cannalyzer
Their inventory, your insights -- organized, optimized.

A Python library and sample program for aggregating dispensary inventory, organizing cannabinoid and terpene data, and exporting tabbed spreadsheet.

## Why LeafTab Exists

When I first got my medical cannabis card, I was fortunate to have knowledgeable budtenders who helped me find strains that worked for me. At first, dispensary inventory was fairly stable, making selection easy. But over time, availability became unpredictable, and finding a good alternative was difficult—especially when newer budtenders weren’t as informed. I eventually realized that terpene and cannabinoid ratios are the key to making good product choices.

The challenge? Even within a single dispensary, comparing products based on terpene and cannabinoid ratios was nearly impossible. Browsing inventory meant opening dozens of browser tabs, jotting down scattered notes, and hoping you’d looked at enough options to find a suitable replacement. And that was before even considering shopping around at other dispensaries! I tried maintaining a personal spreadsheet a few times, but copying and pasting everything took hours—only to be outdated almost immediately.

I knew there had to be a better way. First, I wrote a program to retrieve inventory for a single dispensary. Then, I refined it to be modular—so LeafTab could work across multiple dispensaries, making product comparisons simple, efficient, and accurate.

## Features

* Retrieve and normalize inventory from multiple dispensaries.
* Extract cannabinoid and terpene profiles per product.
* Generate multi-tabbed Excel sheets with conditional formatting.

## Usage

LeafTab automates dispensary inventory retrieval by extracting product details and formatting them into a multi-tabbed spreadsheet for easy comparison. To integrate a new dispensary:

1. Create a new dispensary integration
   * Add a subclass of `Dispensary` inside the `dispensary/` directory.
   * In the constructor, retrieve inventory data and populate `self.inventory` with `list[Product]`.
   * Call `self.process_dataframe()` to convert the inventory into a `DataFrame` for Excel export.
   * Custom methods may be added if needed to handle data retrieval.
2. Modify leaf_tab.py to register the new dispensary class
   * Create an instance of your new Dispensary subclass.
   * Add it to the list of dispensary objects inside leaf_tab.py.
   * This list is then passed to the pre-written write_spreadsheet() method, which automatically generates a multi-tabbed spreadsheet, with each dispensary’s inventory appearing in its own sheet.

### Reverse Engineering Dispensary APIs 

LeafTab retrieves product data by querying dispensary websites. If you need to adapt this for a new dispensary, you'll need to analyze how their site fetches inventory. This typically involves:

- Inspecting network requests in browser dev tools (Chrome/Firefox).
- Identifying API endpoints used for product data. 
- Understanding authentication requirements (if any). 
- Structuring requests to match the site's expected format. 

If you're unfamiliar with this process, check out these resources:

- [How to Reverse Engineer Website APIs](https://blog.apify.com/reverse-engineer-apis/) 
- [FreeCodeCamp’s Guide on Reverse Engineering Websites](https://www.freecodecamp.org/news/how-to-reverse-engineer-a-website/)