# Ballet Performance Scraper

A Python-based web scraper that collects performance data from major international ballet theaters and exports it to Google Sheets and local JSON files.

## Features

- Scrapes performance data from 8 world-renowned theaters:
  - **Bolshoi Theatre** (Russia)
  - **Royal Ballet & Opera** (UK)
  - **Opéra national de Paris** (France)
  - **New National Theatre Tokyo** (Japan)
  - **American Ballet Theatre** (USA)
  - **Vienna State Opera** (Austria)
  - **Mariinsky Theatre** (Russia)
  - **Teatro alla Scala** (Italy)
- **Data Extracted:** Performance title, date, link, description, cast/staff names, main image, and ticket price range (min/max).
- **Multiple Output Formats:**
  - Individual JSON files for each theater in the `data/` directory.
  - Aggregated "Today's" and "Next" performance summary exported to a Google Sheet.
- **Asynchronous Scraping:** Uses `asyncio` and `aiohttp` for efficient data retrieval where possible.
- **Handles Dynamic Content:** Utilizes `undetected-chromedriver` and `selenium` for sites with anti-bot protections.

## Project Structure

- `main.py`: Entry point. Orchestrates the scraping process, data collection, and Google Sheets export.
- `parsers.py`: Contains the parser classes for each specific theater.
- `data/`: Directory where raw JSON performance data is stored.
- `pyproject.toml` / `poetry.lock`: Project dependencies and configuration (managed by Poetry).

## Requirements

- Python 3.10+
- Google Cloud Service Account credentials (for Google Sheets integration).

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ballet-parsing
   ```

2. **Install dependencies:**
   This project uses [Poetry](https://python-poetry.org/) for dependency management.
   ```bash
   poetry install
   ```
   *Alternatively, if you prefer using pip, you can extract dependencies from `pyproject.toml`.*

3. **Google Sheets Setup:**
   - Create a Google Cloud project and enable the Google Sheets and Drive APIs.
   - Create a Service Account and download the JSON key.
   - Rename the key file to `credentials.json` and place it in the project root.
   - Share your target Google Sheet with the Service Account email.

## Usage

Simply run the main script:
```bash
poetry run python main.py
```
Or, if using a virtual environment:
```bash
python main.py
```

The script will:
1. Initialize parsers for all theaters.
2. Scrape performance data and save it to `data/*.json`.
3. Filter the data for today's performances and the next upcoming performance for each theater.
4. Update the "Ballet performances" Google Sheet with the aggregated results.

## Output Details

### Input
The scraper does not require manual input. It fetches data directly from the official websites of the listed theaters.

### Output
1. **Google Sheet:** A sheet named "Ballet performances" with headers for Theater name, link, and details for both today's and the next scheduled performance.
2. **JSON Files:** Raw scraped data for each theater, useful for debugging or further analysis.
3. **Excel:** A local `Parsing results.xlsx` (if generated during testing).

## License

[MIT](LICENSE)
