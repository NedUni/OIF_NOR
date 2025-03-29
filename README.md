
# OIF Ventures Software Engineering Intern Take-Home Task

  

This project is designed to scrape Booking.com listings for Australia for February 1–2, 2026 and serve the data via a Flask API. The scraper uses Selenium with human-like interactions to navigate dynamic content and robust anti-bot measures, storing the results in a CSV file. The Flask API reads the CSV and provides multiple endpoints—including returning the 50 cheapest listings, statistics, search, price filtering, and best-value listings—in JSON format. Additionally, the scraper has been enhanced to save the output CSV with the current date in its filename, allowing users to easily select and deploy data from a specific scrape date.


## Scraper Overview

 *Objective:*
Extract detailed Booking.com listing data (Title, Address, Headline Room Type, Cost in AUD, Review Score, and Number of Reviews) for the specified search parameters.

*Challenge:*
Booking.com imposes a hard limit of 1,000 listings per search. However, the actual number of available listings is much larger because the default search applies a "recommended by us" filter that hides many less-popular properties.

 

 **My Approach - Price Bucketing:**

The scraper divides the overall search space into mutually exclusive price buckets at \$10 intervals.

- For buckets returning fewer than 1,000 listings, all results are captured in a single query.

- For buckets yielding between 1,000 and 2,000 listings, a dual-sorting strategy is employed: first, results are sorted from highest to lowest and the top 1,000 (the more expensive half) are collected; then, sorting is reversed (lowest to highest) to capture the remaining listings.

This method circumvents the 1,000-listing bottleneck and ensures that all available listings are retrieved.

  

**Human-Like Behaviour:**

The scraper emulates natural user behaviour by:

-  *Randomised Delays:* Waiting unpredictable intervals (2–5 seconds) between actions to allow dynamic content to load.

-  *Natural Scrolling and Mouse Movements:* Simulating realistic scrolling and mouse interactions particularly when 'clicking' the show more button.

-  *Explicit Waits:* Using WebDriverWait to ensure that page elements are fully loaded before interacting.

-  *Adaptive Behaviour:* Adjusting interactions based on page state (e.g., clicking “Load more results” only when it appears).

  
 **Anti-Detection Strategies:**
 - *Proxies:* Conceal IP address by routing traffic through proxy servers, making it harder for websites to detect and block your scraper. This is achieved by using a random proxy from https://api.proxyscrape.com.
 - *Undetected ChromeDriver:* Employed a customised ChromeDriver build that bypasses common detection techniques used by websites to identify Selenium-based sessions.

 **Limitations:**
 - A global in-memory set is used to detect and skip duplicates, which is essential when operating in multiple price buckets that might overlap. While storing these items in a set does consume memory, lookups and insertions are effectively O(1) for hashable objects, making this trade-off worthwhile. In the future, an alternative solution could be to use a lightweight database (like SQLite) with a unique constraint on key fields so that duplicate checking happens at the storage level.


**Robustness:**

-   *Incremental Data Persistence:*  
    The program writes data to the CSV file in manageable chunks. Initially, it saves 75 entries during the first load (when the lazy-loaded DOM is populated by Booking.com’s React-based interface), and subsequently in batches of 25 after each "Show more" button press. This ensures that if an error occurs at any point, all successfully scraped data up to that moment is preserved.
    
-   *Duplicate Prevention:* 
    Duplicate entries are prevented by leveraging an in-memory set. Before writing a new entry to CSV, the program checks if it has already been processed. This O(1) duplicate detection mechanism is both efficient and effective, ensuring data integrity.
    
-  *Extensibility:*  
    The system is designed to be adaptable, allowing for the configuration of a unique base URL for searches. For example, the same framework can be used to scrape listings for Budapest on June 10-11, 2026 [(search)](https://www.booking.com/searchresults.en-gb.html?ss=Budapest%2C+Central+Hungary%2C+Hungary&efdco=1&label=gen173nr-1BCAEoggI46AdIM1gEaA-IAQGYAQm4AQfIAQzYAQHoAQGIAgGoAgO4ApCjnr8GwAIB0gIkODE4ZTc3NDUtZTY5Yy00MDNiLWEzN2YtOTNiOTdmMTg5MGFl2AIF4AIB&sid=83dccf7364e141546e8a83efc3ad15bc&aid=304142&lang=en-gb&sb=1&src_elem=sb&src=index&dest_id=-850553&dest_type=city&ac_position=0&ac_click_type=b&ac_langcode=en&ac_suggestion_list_length=5&search_selected=true&search_pageview_id=8f4d2cc8adad009f&ac_meta=GhA4ZjRkMmNjOGFkYWQwMDlmIAAoATICZW46BUJVREFQQABKAFAA&checkin=2026-06-10&checkout=2026-06-11&group_adults=2&no_rooms=1&group_children=0), or any other target market, with no code changes.
    
-   *Resilient Error Handling:*
    Comprehensive use of try-except blocks combined with explicit WebDriverWait ensures that the program gracefully handles exceptions. If an error occurs, the system can refresh the page and resume scraping from where it left off, minimizing data loss and downtime.

## Flask API Overview
Implemented not only the required cheapest listings endpoint but also additional endpoints, along with a command-line interface that allows users to specify the scrape date they wish to query. This enhancement provides greater flexibility, enabling users to select data from different scrape dates and view a range of market insights beyond just the cheapest options.

### `/cheapest`

-   **Description:**  
    Returns a paginated list of the 50 cheapest listings, sorted by cost.
    
  - **Query Parameters:**

     `page` (integer, default: 1) – The page number to retrieve.
        
     `per_page` (integer, default: 50) – The number of listings per page.
    
-   **Justification:**  
    This endpoint provides quick access to the lowest-priced properties, enabling vacationers to identify cheapest holiday—a principle that can be applied to evaluate investment opportunities in other asset classes.
    

### `/stats`

-   **Description:**  
    Provides aggregated market statistics such as average price, median price, total listings, price range, and average review score.
   - **Query Parameters:**
   None
    
-   **Justification:**  
    These statistics offer a comprehensive market snapshot, allowing investors to gauge overall market health and trends, which is vital for informed decision-making in investment contexts.
    

### `/search`

-   **Description:**  
    Enables keyword-based search across property titles and addresses.
  - **Query Parameters:**
     `q` (string) – The keyword to search for in property titles and addresses.

-   **Justification:**  
    This endpoint facilitates targeted data retrieval, helping investors quickly filter and segment markets based on specific criteria, a key capability when scouting for niche investment opportunities.
    

### `/price_range`

-   **Description:**  
    Filters listings within a specified price range.
  - **Query Parameters:**

     `min` (float) – The minimum price for filtering listings.
        
     `max` (float) – The maximum price for filtering listings.
    
-   **Justification:**  
    Isolating properties by price allows investors to analyze specific market segments and compare asset valuations, which is essential for identifying market mispricings and investment targets.
    

### `/best_value`

-   **Description:**  
    Computes a "value score" (review score divided by cost) and returns the top 10 best-value listings within a given price range.
 - **Query Parameters:**

     `min` (float) – The minimum price to filter listings.
        
     `max` (float) – The maximum price to filter listings.
    
-   **Justification:**  
    By quantifying value through quality-to-price ratios, this endpoint helps pinpoint high-potential assets, a methodology that can be extended to assess investment attractiveness in various markets.
    

### `/location_analysis`

-   **Description:**  
    Provides localised market analysis statistics (total listings, average and median prices, price variance, and average review score) for a given location.
    
  - **Query Parameters:**
     `location` (string) – The location (city or region) to analyse
-   **Justification:**  
    This endpoint delivers detailed regional insights, enabling investors to understand local market dynamics and identify areas with attractive investment prospects.
    

### `/property_percentile`

-   **Description:**  
    Given a property name, returns its cost percentile ranking within its location, indicating where it stands relative to local listings.
    
  - **Query Parameters:**
     `name` (string) – The property name to analyse    

-   **Justification:**  
    Comparing a property’s price to its local market distribution highlights relative undervaluation or overvaluation—a critical metric that can be adapted to evaluate investment potential across sectors.
   
   ## Instructions

  

1.  **Install Dependencies:**

In the project directory, run:

```bash

pip3 install -r requirements.txt

```

  

2.  **Run the Scraper:**

Execute the scraper with:

```bash

python3 main.py <URL>

```


  
3.  **Run the API:**

In the same repository, start the Flask API with:

```bash

python3 api.py <DD-MM-YYYY>

```

Access the endpoints (e.g., `http://localhost:5000/cheapest`) via your browser or an API client (Postman, curl).

## Data Table
| Desired Data         | Variable Names       |
|----------------------|----------------------|
| Title                | title                |
| Address              | address              |
| Cost                 | cost                 |
| Review Score         | review_score         |
| Number of Reviews    | number_of_reviews    |
| Room Type            | room_type            |
| URL                  | url                  |


## Conclusion


This project demonstrates a robust and generalisable approach to scraping Booking.com listings despite stringent anti-bot measures and search limitations. By partitioning the search space into $10 price buckets and employing dual-sorting techniques, the scraper circumvents the 1,000-listing cap to produce a comprehensive dataset. The accompanying Flask API provides versatile endpoints for data retrieval, filtering, and statistical analysis, making the solution not only functional but also scalable and extensible.


Happy scraping and API Querying!
---