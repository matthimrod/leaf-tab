# LeafTab: The Cannalyzer
Their inventory, your insights -- organized, optimized.

A Python library for aggregating dispensary inventory, organizing cannabinoid and terpene data, and exporting structured spreadsheets.

## Features

* Retrieve and normalize inventory from multiple dispensaries.
* Extract cannabinoid and terpene profiles per product.
* Generate multi-tabbed Excel sheets with conditional formatting.

## Usage

* Add an extension of the the `Dispensary` class under the `dispensary/` directory for additional integrations.
* Add Dispensary class instances to retrieve a multi-tabbed spreadsheet to make trips to the dispensary easier.

### Reverse Engineering Dispensary APIs 

LeafTab retrieves product data by querying dispensary websites. If you need to adapt this for a new dispensary, you'll need to analyze how their site fetches inventory. This typically involves:

- Inspecting network requests in browser dev tools (Chrome/Firefox).
- Identifying API endpoints used for product data. 
- Understanding authentication requirements (if any). 
- Structuring requests to match the site's expected format. 

If you're unfamiliar with this process, check out these resources:

- [How to Reverse Engineer Website APIs](https://blog.apify.com/reverse-engineer-apis/) 
- [FreeCodeCamp’s Guide on Reverse Engineering Websites](https://www.freecodecamp.org/news/how-to-reverse-engineer-a-website/)