"""
Krugersdorp Golf Club Score History Scraper

This script automates the collection of player score history from handicaps.co.za
for specific players listed in data/players_list.csv.

The script searches for each player individually by their SA Player ID, making it
much more efficient than searching all club members.

Requirements:
- pip install selenium pandas
- Chrome browser installed
- ChromeDriver (will be downloaded automatically with selenium 4.6+)

Usage:
    python golf_scraper.py              # Scrape both scores and player info
    python golf_scraper.py --info-only  # Only update players_info.csv (current HI)
"""

import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time
import re
import os

class GolfScoreScraper:
    def __init__(self, headless=True):
        """Initialize the scraper with Chrome driver"""
        chrome_options = Options()

        if headless:
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--window-size=1920,1080')

        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        self.driver = webdriver.Chrome(options=chrome_options)
        if not headless:
            self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 10)
        self.all_scores = []
        self.all_players_info = []  # Store player info including current HI

    def search_player_by_id(self, player_id, player_name):
        """Search for a specific player by their SA Player ID"""
        print(f"  Searching for {player_name} (ID: {player_id})...")
        self.driver.get("https://www.handicaps.co.za/lookup-golfer/")

        # Wait for page to fully load
        time.sleep(1)

        # Wait for and fill in the player ID search field
        player_id_input = self.wait.until(
            EC.presence_of_element_located((By.ID, "search_player_id"))
        )
        player_id_input.clear()
        player_id_input.send_keys(player_id)

        # Wait a moment for input to register
        time.sleep(0.5)

        # Click search button
        search_button = self.driver.find_element(By.XPATH, "//input[@type='submit'][@value='search']")
        search_button.click()

        # Wait longer for results to load
        time.sleep(3)

    def get_player_info_from_results(self, player_name, sa_player_id):
        """Extract player info from search results when searching by Player ID"""
        try:
            # When searching by Player ID, the player profile loads directly (no search results table)
            # Check if the player profile section is present
            try:
                profile_section = self.wait.until(
                    EC.presence_of_element_located((By.ID, "lookup-profile"))
                )

                # Get the player name from the profile
                profile_name_elem = profile_section.find_element(By.XPATH, ".//div[@class='profile-info-player']/p[1]")
                profile_name = profile_name_elem.text.strip()

                print(f"  Found player profile: {profile_name}")

                # Extract current Handicap Index from the profile
                # The HI is in: div.profile-handicap-index > em
                current_hi = None
                try:
                    hi_elem = profile_section.find_element(By.XPATH, ".//div[@class='profile-handicap-index']/em")
                    hi_text = hi_elem.text.strip()
                    # Extract just the number (may have + or - prefix, or S suffix for soft cap)
                    hi_match = re.search(r'([+-]?\d+\.?\d*)', hi_text)
                    if hi_match:
                        current_hi = hi_match.group(1)
                    print(f"  Current Handicap Index: {current_hi}")
                except NoSuchElementException:
                    print(f"  Could not find Handicap Index element")
                except Exception as e:
                    print(f"  Error extracting HI: {e}")

                # The internal player ID is the same as SA Player ID when searching directly
                # We'll use the SA Player ID as the internal ID for the JavaScript call
                return {
                    'name': player_name,
                    'player_id': sa_player_id,  # Use SA Player ID as internal ID
                    'sa_player_id': sa_player_id,
                    'current_hi': current_hi
                }

            except TimeoutException:
                # If no profile section, check for "no results" message
                try:
                    no_results = self.driver.find_element(By.XPATH, "//*[contains(text(), 'No results found')]")
                    if no_results:
                        print(f"  No results found for {player_name} (ID: {sa_player_id})")
                        print(f"  Note: Player ID may be incorrect or player may not be in the system")
                        return None
                except NoSuchElementException:
                    pass

                print(f"  Timeout waiting for player profile for {player_name}")
                return None

        except Exception as e:
            print(f"  Error extracting player info: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_player_score_history(self, player_info, already_loaded=False):
        """Extract score history for a specific player"""
        print(f"  Extracting score history...")

        try:
            # If not already loaded (e.g., from club search), execute the JavaScript function
            if not already_loaded:
                # Execute the JavaScript function to load player profile
                self.driver.execute_script(f"getPlayerProfile({player_info['player_id']})")

                # Wait for the player profile section to load
                print("  Waiting for player profile to load...")
                time.sleep(3)

            # Wait for the score history table to be present
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "player-history-table"))
                )
            except TimeoutException:
                print("  Score history table not found, skipping player")
                return []

            player_scores = []

            # Check if there are multiple pages of scores
            try:
                page_limit_elem = self.driver.find_element(
                    By.XPATH,
                    "//section[@class='player-score-history']//span[@class='page-limit']"
                )
                total_pages = int(page_limit_elem.text)
                print(f"  Found {total_pages} page(s) of scores")
            except:
                total_pages = 1
                print("  Single page of scores")

            # Loop through all pages of score history
            for page_num in range(1, total_pages + 1):
                if page_num > 1:
                    print(f"  Loading page {page_num}...")
                    # Click next button for score history
                    try:
                        next_button = self.driver.find_element(
                            By.XPATH,
                            "//a[@onclick='paginatePlayerScoreNext()']"
                        )
                        next_button.click()
                        time.sleep(2)
                    except:
                        print(f"  Could not navigate to page {page_num}, stopping")
                        break

                # Extract scores from current page
                score_rows = self.driver.find_elements(
                    By.XPATH,
                    "//table[@class='player-history-table table table-striped table-condensed table-hover cf']//tbody//tr"
                )

                for row in score_rows:
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")

                        # Need at least 12 cells for complete data
                        if len(cells) < 11:
                            continue

                        # Extract club name (remove the course details in <i> tag)
                        club_text = cells[2].text.strip()
                        club_name = club_text.split('\n')[0] if '\n' in club_text else club_text

                        # Extract tee value and color (the number inside the colored box)
                        tee_div = cells[3].find_element(By.XPATH, ".//div[@class='tee tee_input']")
                        tee_span = tee_div.find_element(By.TAG_NAME, "span")
                        tee_value = tee_span.text.strip()

                        # Extract the background color of the tee box
                        tee_color = tee_div.value_of_css_property("background-color")

                        # Convert RGB color to hex for readability (optional)
                        try:
                            # Parse rgb(r, g, b) format
                            if tee_color.startswith('rgb'):
                                rgb = tee_color.replace('rgb(', '').replace('rgba(', '').replace(')', '').split(',')
                                r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
                                tee_color_hex = f"#{r:02x}{g:02x}{b:02x}".upper()
                            else:
                                tee_color_hex = tee_color
                        except:
                            tee_color_hex = tee_color

                        # Extract diff value (remove <u> and <sup> tags)
                        diff_text = cells[10].text.strip()

                        score_data = {
                            'Player Name': player_info['name'],
                            'SA Player ID': player_info['sa_player_id'],
                            'Date Played': cells[0].text.strip(),
                            'Club Played': club_name,
                            'Tee': tee_value,
                            'Tee Color': tee_color_hex,
                            'CR': cells[4].text.strip(),
                            'SLOPE': cells[5].text.strip(),
                            'OPEN HI': cells[6].text.strip(),
                            'CH': cells[7].text.strip(),
                            'GROSS': cells[8].text.strip(),  # This is actually adj gross
                            'DIFF': diff_text
                        }

                        player_scores.append(score_data)

                    except Exception as e:
                        print(f"  Error extracting row data: {e}")
                        continue

                print(f"  Page {page_num}: Extracted {len(score_rows)} score(s)")

            print(f"  Total: {len(player_scores)} scores for this player")
            return player_scores

        except Exception as e:
            print(f"  Error processing player {player_info['name']}: {e}")
            import traceback
            traceback.print_exc()
            return []

    def load_player_ids_from_csv(self, csv_path):
        """Load player IDs from CSV file"""
        print(f"Loading player IDs from {csv_path}...")
        try:
            df = pd.read_csv(csv_path)
            # Strip whitespace from player IDs and names
            player_ids = df['Player ID'].astype(str).str.strip().tolist()
            player_names = df['Name'].str.strip().tolist()
            print(f"Loaded {len(player_ids)} player IDs from CSV")
            return list(zip(player_names, player_ids))
        except Exception as e:
            print(f"Error loading CSV file: {e}")
            return []

    def scrape_all_players(self, csv_path, info_only=False):
        """Main method to scrape players from CSV file

        Args:
            csv_path: Path to CSV file with player IDs
            info_only: If True, only collect player info (current HI), skip score history
        """
        try:
            # Load player IDs from CSV
            target_players_list = self.load_player_ids_from_csv(csv_path)
            if not target_players_list:
                print("No players loaded from CSV. Exiting.")
                return

            mode_str = "player info only" if info_only else "scores and player info"
            print(f"\nWill scrape {len(target_players_list)} players ({mode_str})\n")

            # Process each player directly by ID
            for i, (player_name, player_id) in enumerate(target_players_list, 1):
                print(f"\n{'='*60}")
                print(f"[{i}/{len(target_players_list)}] Processing {player_name}")
                print(f"{'='*60}")

                try:
                    # Search for this specific player
                    self.search_player_by_id(player_id, player_name)

                    # Get the player info from search results
                    player_info = self.get_player_info_from_results(player_name, player_id)

                    if player_info:
                        # Store player info (including current HI)
                        self.all_players_info.append({
                            'Player Name': player_info['name'],
                            'SA Player ID': player_info['sa_player_id'],
                            'Current HI': player_info.get('current_hi')
                        })

                        # Get score history (skip if info_only mode)
                        if not info_only:
                            scores = self.get_player_score_history(player_info, already_loaded=True)
                            self.all_scores.extend(scores)
                    else:
                        print(f"  Could not find player info in search results")

                except Exception as e:
                    print(f"  Error processing {player_name}: {e}")
                    continue

                # Be respectful to the server - add delay between requests
                time.sleep(1.0 if info_only else 1.5)

            print(f"\n\n{'='*60}")
            print(f"SCRAPING COMPLETE")
            print(f"{'='*60}")
            if not info_only:
                print(f"Total scores collected: {len(self.all_scores)}")
            print(f"Total players processed: {len(target_players_list)}")

        except Exception as e:
            print(f"Error during scraping: {e}")
            import traceback
            traceback.print_exc()

    def save_to_csv(self, scores_file=None, players_file="players_info.csv"):
        """Save collected data to CSV files (scores and player info)"""
        print(f"\n{'='*60}")
        print(f"DATA SAVED")
        print(f"{'='*60}")

        # Save scores (if scores_file is provided)
        if scores_file:
            if self.all_scores:
                df_scores = pd.DataFrame(self.all_scores)
                df_scores.to_csv(scores_file, index=False)
                print(f"\nScores file: {scores_file}")
                print(f"  Total records: {len(df_scores)}")
                print(f"  Unique players: {df_scores['Player Name'].nunique()}")
                print(f"  Columns: {', '.join(df_scores.columns.tolist())}")
            else:
                print("\nNo score data to save!")

        # Save player info
        if self.all_players_info:
            df_players = pd.DataFrame(self.all_players_info)
            df_players.to_csv(players_file, index=False)
            print(f"\nPlayers file: {players_file}")
            print(f"  Total players: {len(df_players)}")
            print(f"  Columns: {', '.join(df_players.columns.tolist())}")
        else:
            print("\nNo player info to save!")

    def close(self):
        """Close the browser"""
        self.driver.quit()
        print("\nBrowser closed.")


def main():
    """Main execution function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Scrape golf scores from handicaps.co.za')
    parser.add_argument('--info-only', action='store_true',
                        help='Only update players_info.csv (current HI), skip score history')
    args = parser.parse_args()

    # Run in headless mode by default (set to False to see the browser)
    scraper = GolfScoreScraper(headless=True)

    try:
        print("="*60)
        print("KRUGERSDORP GOLF CLUB SCORE SCRAPER")
        print("="*60)
        if args.info_only:
            print("\nMode: INFO-ONLY (updating current HI only)")
        print("\nRunning in headless mode (no browser window)")
        print("\nStarting scrape...")

        # Create outputs folder if it doesn't exist
        os.makedirs("outputs", exist_ok=True)

        # Path to the CSV file with player IDs
        csv_path = "data/players_list.csv"

        # Scrape only players listed in the CSV
        scraper.scrape_all_players(csv_path=csv_path, info_only=args.info_only)

        # Save results to outputs folder
        if args.info_only:
            # Only save players_info.csv
            scraper.save_to_csv(
                scores_file=None,
                players_file="outputs/players_info.csv"
            )
        else:
            # Save both files
            scraper.save_to_csv(
                scores_file="outputs/scores.csv",
                players_file="outputs/players_info.csv"
            )

    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
