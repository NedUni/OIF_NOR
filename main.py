from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from fake_useragent import UserAgent
import undetected_chromedriver as uc
import time
import random
import csv
import json
import sys
from datetime import datetime

class BookingScraper:
    def __init__(self, csv_file, proxy):
        self.driver = self._init_driver(self.get_proxy())
        self.csv_file = csv_file
        self.fieldnames = ["title", "address", "cost", "review_score", "number_of_reviews", "room_type", "url"]
        self._init_csv()
        self.listings = set()
    
    def _init_driver(self, proxy):
        print("Initialising driver...")

        #Need to check
        try:
            user_agent = UserAgent(browsers=["chrome"])
            options = uc.ChromeOptions()
            options.add_argument(f'user-agent={user_agent.chrome}')
            options.add_argument('--disable-notifications')
            options.add_argument(f'--proxy-server=http://{proxy}')
            driver = uc.Chrome(enable_cdp_events=True, options=options)
        except:
            user_agent = UserAgent(browsers=["chrome"])
            options = uc.ChromeOptions()
            options.add_argument(f'user-agent={user_agent.chrome}')
            options.add_argument('--disable-notifications')
            driver = uc.Chrome(enable_cdp_events=True, options=options)
            
        return driver
    
    def get_proxy(self):
        response = requests.get('https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text')
        proxies = response.text.splitlines()
        cleaned_proxies = [proxy.split('://')[-1] for proxy in proxies]
        random.shuffle(cleaned_proxies)
        return cleaned_proxies[0]

    def _init_csv(self):
        with open(self.csv_file, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writeheader()

    def handle_no_such_element_exception(self, data_extraction_task):
        try:
            return data_extraction_task()
        except NoSuchElementException:
            return None

    def handle_get_review_score(self, data_extraction_task):
        try:
            text = data_extraction_task()
            lines = text.splitlines()
            return lines[1] if len(lines) > 1 else "New to Booking.com"
        except NoSuchElementException:
            return "New to Booking.com"

    def handle_get_review_count(self, data_extraction_task):
        try:
            text = data_extraction_task()
            lines = text.splitlines()
            if len(lines) > 3:
                parts = lines[3].split()
                if parts:
                    return parts[0]
            return 0
        except NoSuchElementException:
            return 0

    def get_address(self, url):
        self.driver.execute_script("window.open(arguments[0], '_blank');", url)
        self.driver.switch_to.window(self.driver.window_handles[-1])
       
        time.sleep(random.uniform(3, 5))

        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='PropertyHeaderAddressDesktop-wrapper']"))
            )
            address_text = element.text
        except TimeoutException:
            address_text = None

        address = address_text.splitlines()[0] if address_text else None

        self.driver.close()
        
        self.driver.switch_to.window(self.driver.window_handles[0])
        
        time.sleep(random.uniform(3, 5))
        
        return address

    def scrape(self, items):
        results = []
        for x in items:
            title = self.handle_no_such_element_exception(
                lambda: x.find_element(By.CSS_SELECTOR, "[data-testid='title']").text
            )
            cost_text = self.handle_no_such_element_exception(
                lambda: x.find_element(By.CSS_SELECTOR, "[data-testid='price-and-discounted-price']").text
            )
            cost = cost_text.split()[1] if cost_text else None

            review_score = self.handle_get_review_score(
                lambda: x.find_element(By.CSS_SELECTOR, "[data-testid='review-score']").text
            )
            number_of_reviews = self.handle_get_review_count(
                lambda: x.find_element(By.CSS_SELECTOR, "[data-testid='review-score']").text
            )
            room_type_text = self.handle_no_such_element_exception(
                lambda: x.find_element(By.CSS_SELECTOR, "[data-testid='recommended-units']").text
            )
            room_type = room_type_text.splitlines()[0] if room_type_text else None

            # Get detail page URL for address
            # detail_link = x.find_element(
            #     By.CSS_SELECTOR, "a[target='_blank'][rel='noopener noreferrer']"
            # ).get_attribute("href")

            address = self.handle_no_such_element_exception(lambda: x.find_element(By.CSS_SELECTOR, "[data-testid=\"address\"]").text)

            url = x.find_element(
                By.CSS_SELECTOR, "a[target='_blank'][rel='noopener noreferrer']"
            ).get_attribute("href")

            # address = self.get_address(detail_link)

            item = {
                "title": title,
                "address": address,
                "cost": cost,
                "review_score": review_score,
                "number_of_reviews": number_of_reviews,
                "room_type": room_type,
                "url": url
            }

            hashable_item = frozenset(item.items())
            if hashable_item not in self.listings:
                results.append(item)
                self.listings.add(hashable_item)

        return results

    def append_to_csv(self, data):
        with open(self.csv_file, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            for row in data:
                writer.writerow(row)

    def scroll_page(self, total_number):

        this_count = 0
        
        while this_count < total_number:
            while True:
                try:
                    last_height = self.driver.execute_script("return document.body.scrollHeight") 
                    break
                except:
                    time.sleep(random.uniform(3, 5))

            while True:
                if total_number > 20:
                    self.driver.execute_script("window.scrollBy(0, document.body.scrollHeight);")
                    time.sleep(random.uniform(3, 5))
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height
                else:
                    break

            property_items = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='property-card']")
            new_property_items = property_items[this_count:]
            recent_scrape = self.scrape(new_property_items)
            self.append_to_csv(recent_scrape)
            print(f"Just scraped {len(recent_scrape)} new items.")
            this_count = len(property_items)

            try:
                # Find Button
                load_more_button = self.driver.find_element(
                    By.XPATH, "//span[text()='Load more results']/ancestor::button"
                )

                # Scroll to the button positon with some randomness
                button_y_position = self.driver.execute_script(
                    "return arguments[0].getBoundingClientRect().top + window.pageYOffset;",
                    load_more_button
                )
                offset = random.randint(20, 50)
                target_y_position = button_y_position - offset
                self.driver.execute_script("window.scrollTo(0, arguments[0]);", target_y_position)


                # Sleep some random time then click then sleep again
                time.sleep(random.uniform(3, 5))
                load_more_button.click()
                print("Clicked 'Load more results' button. Waiting for next batch...")
                time.sleep(random.uniform(3, 5))

            except Exception as e:
                print("No more results...")
                break

    def load_page(self, url):
        
        self.driver.get(url)
        
        #give tghis some time
        while True:
            try:
                num_in_price_range = int(
                    self.driver.find_elements(By.CSS_SELECTOR, '[aria-live="assertive"]')[0]
                    .text.split()[1].replace(",", "")
                )
                break
            except Exception as e:
                print("Error reading number of properties:", e)
                time.sleep(random.uniform(3, 5))

        print(f"Number of properties in range: {num_in_price_range}")
        
        # If number of listings are less than 1,000 for sub-query simply scrape each of them
        if num_in_price_range < 1000:
            self.scroll_page(num_in_price_range)
        
        # If number of listings are greater than 1,000 for sub-query, must scrape top 1,000 by price, then scape remaining number but from least to highest cost
        else:
            while True:
                try:
        
                    # Scroll to top of screen and select high-to-low filter
                    self.driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(random.uniform(3, 5))
                    sorters_dropdown_trigger = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="sorters-dropdown-trigger"]')
                    sorters_dropdown_trigger.click()
                    WebDriverWait(self.driver, 30).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, 'button[data-id="price_from_high_to_low"]'))
                    )
                    price_highest_option = self.driver.find_element(By.CSS_SELECTOR, 'button[data-id="price_from_high_to_low"]')
                    price_highest_option.click()

                    time.sleep(random.uniform(3, 5))

                    # Scrape result
                    print("Beginning to scrape first 1,000 of price bucket")
                    self.scroll_page(1000)

                    break

                except TimeoutException:
                    # Wait for dropdown to appear, if not refresh and try again
                    print("Element not visible after 30 seconds, retrying")
                    time.sleep(random.uniform(3, 5))
                    self.driver.refresh()

            print("Collected 1st 1000. Begining to collect 2nd half of this price bucket")
            time.sleep(random.uniform(3, 5))

            while True:
                try:
                    # Scroll to top of screen and select low-to-high filter
                    self.driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(random.uniform(3, 5))
                    sorters_dropdown_trigger = self.driver.find_element(By.CSS_SELECTOR, '[data-testid="sorters-dropdown-trigger"]')
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", sorters_dropdown_trigger)
                    sorters_dropdown_trigger.click()
                    WebDriverWait(self.driver, 30).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, 'button[data-id="price"]'))
                    )
                    price_highest_option = self.driver.find_element(By.CSS_SELECTOR, 'button[data-id="price"]')
                    price_highest_option.click()
                    
                    time.sleep(random.uniform(3, 5))

                    # Scrape result
                    print("Beginning to scrape remaining of price bucket")
                    remaining = num_in_price_range - 1000
                    self.scroll_page(remaining)

                    break
                
                except TimeoutException:
                    # Wait for dropdown to appear, if not refresh and try again
                    print("Element not visible after 30 seconds, retrying")
                    time.sleep(random.uniform(3, 5))
                    self.driver.refresh()


    def close(self):
        self.driver.quit()

###############################
#         Main Script         #
###############################

if __name__ == '__main__':

    current_date = datetime.now().strftime("%d-%m-%Y")
    csv_file = "output/{current_date}.csv"
    scraper = BookingScraper(csv_file)

    # Main search URL
    search_url = (
        "https://www.booking.com/searchresults.html"
        "?ss=Australia"
        "&checkin_year=2026&checkin_month=2&checkin_monthday=1"
        "&checkout_year=2026&checkout_month=2&checkout_monthday=2"
        "&group_adults=2&group_children=0&no_rooms=1&selected_currency=AUD"
    )

    if len(sys.argv) > 1:
        search_url = sys.argv[1]
    
    try:
        scraper.driver.get(search_url)
    except:
        print("Looks like your URL is invalid. Try something like this:\nhttps://www.booking.com/searchresults.en-gb.html?ss=Nice%2C+Provence-Alpes-C%C3%B4te+d%27Azur%2C+France&ssne=Australia&ssne_untouched=Australia&efdco=1&label=gen173nr-1BCAEoggI46AdIM1gEaA-IAQGYAQm4AQfIAQzYAQHoAQGIAgGoAgO4Aryon78GwAIB0gIkMjk0Mjc0YzctZmZlOC00OGEwLWEzY2EtZWE4NjBjZmFlODY52AIF4AIB&sid=83dccf7364e141546e8a83efc3ad15bc&aid=304142&lang=en-gb&sb=1&src_elem=sb&src=index&dest_id=-1454990&dest_type=city&ac_position=0&ac_click_type=b&ac_langcode=en&ac_suggestion_list_length=5&search_selected=true&search_pageview_id=adca4e1ebc7a03a7&ac_meta=GhBhZGNhNGUxZWJjN2EwM2E3IAAoATICZW46BE5pY2VAAEoAUAA%3D&checkin=2026-06-10&checkout=2026-06-11&group_adults=2&no_rooms=1&group_children=0")
        sys.exit(1)


    print(f"Beginning scrape...")

    # Build price buckets to cope with 1,000 listing cap
    price_ranges = []
    price_ranges.append(("min", "20"))
    for lower in range(21, 890, 10):
        upper = lower + 9
        price_ranges.append((str(lower), str(upper)))
    price_ranges.append(("890", "max"))

    # Iterate over each price bucket and scrape all data
    for (lower, upper) in price_ranges:
        nflt_value = f"price%3DAUD-{lower}-{upper}-1"
        final_url = f"{search_url}&nflt={nflt_value}"
        print(f"Scraping URL for range {lower} to {upper}: {final_url}")
        scraper.load_page(final_url)
        time.sleep(random.uniform(3, 5))

    
    print("Scape is complete")
    print("Result has been stored in", csv_file)
    print(f"Total expected properties: {number_of_properties}")


    scraper.close()
