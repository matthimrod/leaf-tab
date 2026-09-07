# LeafTab Development Instructions

## Build, Test, and Lint
- **Install Dependencies**: Use `uv sync` to install project dependencies.
- **Linting**: Use `ruff check .` to check for linting issues.
- **Formatting**: Use `ruff format .` to format the code.
- **Type Checking**: Use `mypy .` to run type checks.
- **Running the Program**: Execute the main script using `python leaf_tab.py`.

## High-Level Architecture
LeafTab is a Python utility designed to aggregate and normalize cannabis dispensary inventory data into a multi-tabbed Excel spreadsheet.

- **Core Logic (`leaf_tab.py`)**: The entry point of the application. It registers various dispensary instances and triggers the spreadsheet generation process.
- **Data Model (`dispensary/__init__.py`)**: Defines the core `Product` dataclass and the base `Dispensary` class. The `Dispensary` class handles common logic like:
    - Normalizing inventory data into a pandas DataFrame.
    - Building URLs for API requests.
    - Formatting and writing the final Excel file using `xlsxwriter`.
- **Dispensary Integrations (`dispensary/`)**: Each file in this directory (e.g., `ethos.py`, `rise.py`, `zenleaf.py`) contains a subclass of `Dispensary` tailored to a specific dispensary's API. These classes handle:
    - Fetching inventory data (often using `requests` and `concurrent.futures` for parallel requests).
    - Parsing complex JSON responses into the standard `Product` format.
    - Handling specific API quirks like pagination, authentication, and custom weight/price logic.

## Key Conventions
- **Data Normalization**: Every dispensary integration must map its unique API response to the standard `Product` dataclass.
- **Parallel Requests**: Use `concurrent.futures.ThreadPoolExecutor` within dispensary classes to fetch individual product details in parallel to improve performance.
- **Excel Formatting**: The `Dispensary.write_spreadsheet` method applies specific conditional formatting (e.g., color-coding by strain type) and column widths based on the normalized data.
- **Pydantic Models**: Use Pydantic models for robust validation of API responses within the dispensary integration files.
- **Weight Mapping**: Standardize various weight strings (e.g., "sub_half", "half_gram", "gram", "two_gram") across different dispensaries.
