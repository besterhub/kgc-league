"""
ScoreCapture Match Play Results Scraper

This script scrapes match play results from scorecapture.com for CGGU leagues
to generate win/loss/draw records for Krugersdorp Golf Club players.

The script uses click-based navigation on the Seasons page rather than direct URLs,
as the website requires JavaScript interactions.

Requirements:
- pip install selenium pandas
- Chrome browser installed
- ChromeDriver (will be downloaded automatically with selenium 4.6+)

Usage:
    python matchplay_scraper.py                    # Discover and scrape CGGU Betterball
    python matchplay_scraper.py --no-headless      # Show browser for debugging
"""

import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    StaleElementReferenceException, ElementClickInterceptedException
)
from selenium.webdriver.common.action_chains import ActionChains
import pandas as pd
import time
import re
import os
from collections import defaultdict


class MatchPlayScraper:
    def __init__(self, headless=True):
        """Initialize the scraper with Chrome driver"""
        chrome_options = Options()

        if headless:
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--window-size=1920,1080')

        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-notifications')

        self.driver = webdriver.Chrome(options=chrome_options)
        if not headless:
            self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 15)
        self.short_wait = WebDriverWait(self.driver, 5)
        self.base_url = "https://www.scorecapture.com"

        # Store results
        self.all_matches = []
        self.player_records = defaultdict(lambda: {'wins': 0, 'losses': 0, 'draws': 0, 'matches': []})

    def load_player_list(self, csv_path="data/players_list.csv"):
        """Load player names from CSV to match against"""
        try:
            df = pd.read_csv(csv_path)
            players = df['Name'].str.strip().tolist()
            print(f"Loaded {len(players)} players from {csv_path}")
            return players
        except Exception as e:
            print(f"Error loading player list: {e}")
            return []

    def normalize_name(self, name):
        """Normalize player name for matching"""
        if not name:
            return ""
        name = ' '.join(name.strip().lower().split())
        return name

    def match_player(self, scraped_name, player_list):
        """Try to match scraped name to player list"""
        normalized_scraped = self.normalize_name(scraped_name)

        for player in player_list:
            normalized_player = self.normalize_name(player)

            # Exact match
            if normalized_scraped == normalized_player:
                return player

            # Check if one contains the other
            scraped_parts = set(normalized_scraped.split())
            player_parts = set(normalized_player.split())

            # If at least first and last name match
            if len(scraped_parts & player_parts) >= 2:
                return player

            # Check surname and first name start
            if len(scraped_parts) >= 2 and len(player_parts) >= 2:
                scraped_list = normalized_scraped.split()
                player_list_parts = normalized_player.split()
                scraped_last = scraped_list[-1]
                player_last = player_list_parts[-1]

                if scraped_last == player_last:
                    scraped_first = scraped_list[0]
                    player_first = player_list_parts[0]
                    if (scraped_first == player_first or
                        scraped_first.startswith(player_first[:3]) or
                        player_first.startswith(scraped_first[:3])):
                        return player

        return None

    def navigate_to_seasons(self, click_history=True):
        """Navigate to the seasons page

        Args:
            click_history: If True, click "View History" to show older seasons (default: True)
        """
        print("Navigating to ScoreCapture Seasons page...")
        self.driver.get(f"{self.base_url}/scorecapture/Fixtures/Seasons")
        time.sleep(3)

        # Wait for page to load
        try:
            self.wait.until(EC.presence_of_element_located((By.ID, "SeasonList")))
            print("Seasons page loaded successfully")
        except TimeoutException:
            print("Warning: SeasonList element not found, page may not have loaded correctly")

        # Always click "View History" button to show older seasons (page resets after navigation)
        if click_history:
            self.click_view_history()

    def click_view_history(self):
        """Click the View History button to show older seasons"""
        print("Looking for 'View History' button...")

        try:
            # The button has id="History"
            history_btn = self.driver.find_element(By.ID, "History")
            btn_text = history_btn.text.strip()
            print(f"  Found History button with text: '{btn_text}'")

            # Only click if it says "View History" (not "View Current")
            if 'history' in btn_text.lower():
                print(f"  Clicking to show historical seasons...")
                self.click_element_safely(history_btn)
                time.sleep(3)  # Wait for history to load
                print("  Historical seasons loaded")
                return True
            else:
                print(f"  Already showing history (button says '{btn_text}')")
                return True

        except NoSuchElementException:
            print("  History button not found by ID, trying other selectors...")

            # Fallback to other selectors
            selectors = [
                "//button[contains(text(), 'View History')]",
                "//button[contains(text(), 'History')]",
            ]

            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        if elem.is_displayed():
                            print(f"  Found button, clicking...")
                            self.click_element_safely(elem)
                            time.sleep(3)
                            return True
                except:
                    continue

            print("  'View History' button not found")
            return False

        except Exception as e:
            print(f"  Error clicking View History: {e}")
            return False

    def click_element_safely(self, element):
        """Click an element with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Scroll element into view
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.5)

                # Try clicking
                element.click()
                return True

            except ElementClickInterceptedException:
                # Try JavaScript click
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception:
                    pass

            except StaleElementReferenceException:
                return False

            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"  Failed to click element: {e}")

            time.sleep(0.5)

        return False

    def get_all_cggu_divisions_info(self):
        """Get ALL CGGU division info across all seasons"""
        print("\nExtracting ALL CGGU divisions from all seasons...")

        divisions = []

        try:
            # Find all Season blocks
            season_blocks = self.driver.find_elements(By.CSS_SELECTOR, "div.Season")
            print(f"Found {len(season_blocks)} total season blocks")

            for season in season_blocks:
                try:
                    # Check if this is CGGU
                    season_text = season.text.upper()
                    if 'CGGU' not in season_text:
                        continue

                    # Get season name and date range
                    try:
                        season_name_elem = season.find_element(By.XPATH,
                            ".//div[@data-original-title='Season Name']")
                        season_name = season_name_elem.text.strip()
                    except:
                        season_name = "Unknown Season"

                    try:
                        season_date_elem = season.find_element(By.XPATH,
                            ".//div[@data-original-title='Season Date']")
                        season_date = season_date_elem.text.strip()
                    except:
                        season_date = ""

                    print(f"\nProcessing CGGU Season: {season_name} ({season_date})")

                    # Get all divisions with PlayersResults icons
                    players_results_icons = season.find_elements(By.CSS_SELECTOR, "i.PlayersResults")

                    for icon in players_results_icons:
                        try:
                            div_id = icon.get_attribute("data-id")

                            # Get the parent Division element to find division name
                            div_elem = icon.find_element(By.XPATH, "./ancestor::div[contains(@class, 'Division')]")
                            div_name_elem = div_elem.find_element(By.XPATH,
                                ".//div[@data-original-title='Division Name']")
                            div_name = div_name_elem.text.strip()

                            # Get League name
                            league_elem = icon.find_element(By.XPATH,
                                "./ancestor::div[contains(@class, 'League')]//div[@data-original-title='League Name']")
                            league_name = league_elem.text.strip()

                            # Clean up names (remove icons)
                            div_name = re.sub(r'[\uf111\uf056\uf055]', '', div_name).strip()
                            league_name = re.sub(r'[\uf111\uf056\uf055]', '', league_name).strip()

                            divisions.append({
                                'season': season_name,
                                'season_date': season_date,
                                'league': league_name,
                                'division': div_name,
                                'division_id': div_id,
                                'icon_element': icon
                            })

                            print(f"  Found: {league_name} / {div_name} (ID: {div_id})")

                        except Exception as e:
                            continue

                except Exception as e:
                    continue

        except Exception as e:
            print(f"Error getting divisions: {e}")
            import traceback
            traceback.print_exc()

        print(f"\nTotal CGGU divisions found across all seasons: {len(divisions)}")
        return divisions

    def get_cggu_divisions_info(self):
        """Get CGGU division info - wrapper that calls get_all_cggu_divisions_info"""
        return self.get_all_cggu_divisions_info()

    def click_leaderboard_icon(self, division_id):
        """Click on the leaderboard icon for a division"""
        try:
            # Find the DivLDB icon with matching data-id
            icon = self.driver.find_element(By.CSS_SELECTOR, f"i.DivLDB[data-id='{division_id}']")
            self.click_element_safely(icon)
            time.sleep(2)
            return True
        except NoSuchElementException:
            print(f"  Leaderboard icon not found for division {division_id}")
            return False
        except Exception as e:
            print(f"  Error clicking leaderboard: {e}")
            return False

    def click_players_results_icon(self, division_id):
        """Click on the PlayersResults icon for a division"""
        try:
            icon = self.driver.find_element(By.CSS_SELECTOR, f"i.PlayersResults[data-id='{division_id}']")
            self.click_element_safely(icon)
            time.sleep(2)
            return True
        except NoSuchElementException:
            print(f"  PlayersResults icon not found for division {division_id}")
            return False
        except Exception as e:
            print(f"  Error clicking PlayersResults: {e}")
            return False

    def click_fixtures_icon(self, division_id):
        """Click on the DivFix (fixtures) icon for a division"""
        try:
            icon = self.driver.find_element(By.CSS_SELECTOR, f"i.DivFix[data-id='{division_id}']")
            self.click_element_safely(icon)
            time.sleep(2)
            return True
        except NoSuchElementException:
            print(f"  Fixtures icon not found for division {division_id}")
            return False
        except Exception as e:
            print(f"  Error clicking fixtures: {e}")
            return False

    def check_modal_for_krugersdorp(self):
        """Check if current modal/popup contains Krugersdorp"""
        time.sleep(1)

        try:
            # Look for modal content
            modals = self.driver.find_elements(By.CSS_SELECTOR,
                ".modal, .popup, [role='dialog'], .modal-content, .modal-body")

            for modal in modals:
                if modal.is_displayed():
                    modal_text = modal.text.lower()
                    if 'krugersdorp' in modal_text or 'kgc' in modal_text:
                        return True, modal_text

            # Also check page body
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            if 'krugersdorp' in body_text or 'kgc' in body_text:
                return True, body_text

        except Exception as e:
            print(f"  Error checking for Krugersdorp: {e}")

        return False, ""

    def close_modal(self):
        """Close any open modal/popup"""
        try:
            # Try various close button selectors
            close_selectors = [
                "button.close", ".modal .close", "[data-dismiss='modal']",
                ".btn-close", ".modal-close", "button[aria-label='Close']"
            ]

            for selector in close_selectors:
                try:
                    close_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if close_btn.is_displayed():
                        close_btn.click()
                        time.sleep(0.5)
                        return True
                except:
                    continue

            # Try pressing Escape
            from selenium.webdriver.common.keys import Keys
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(0.5)

        except:
            pass

        return False

    def extract_player_results_from_modal(self):
        """Extract player W/L/D data from the current modal"""
        results = []

        try:
            # Wait a moment for modal content to load
            time.sleep(1)

            # Find tables in modal or page
            tables = self.driver.find_elements(By.TAG_NAME, "table")

            for table in tables:
                if not table.is_displayed():
                    continue

                rows = table.find_elements(By.TAG_NAME, "tr")

                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        # First cell usually contains player name
                        player_name = cells[0].text.strip()

                        if player_name and not player_name.isdigit():
                            result = {'player_name': player_name}

                            # Try to extract numeric values from remaining cells
                            for i, cell in enumerate(cells[1:], 1):
                                cell_text = cell.text.strip()
                                if cell_text.isdigit():
                                    if 'played' not in result:
                                        result['played'] = int(cell_text)
                                    elif 'wins' not in result:
                                        result['wins'] = int(cell_text)
                                    elif 'losses' not in result:
                                        result['losses'] = int(cell_text)
                                    elif 'draws' not in result:
                                        result['draws'] = int(cell_text)

                            if 'wins' in result or 'losses' in result:
                                results.append(result)

        except Exception as e:
            print(f"  Error extracting results: {e}")

        return results

    def check_page_for_krugersdorp(self):
        """Check if current page contains Krugersdorp"""
        time.sleep(2)

        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            if 'krugersdorp' in body_text or 'kgc' in body_text:
                return True, body_text
        except Exception as e:
            print(f"  Error checking page: {e}")

        return False, ""

    def scan_for_krugersdorp(self, divisions, player_list):
        """Scan divisions to find Krugersdorp club, then match players"""
        print("\n" + "="*60)
        print("SCANNING FOR KRUGERSDORP IN CGGU DIVISIONS")
        print("="*60)

        krugersdorp_divisions = []

        # Focus on Betterball League first (most likely for your team)
        betterball_divs = [d for d in divisions if 'betterball' in d['league'].lower()]
        other_divs = [d for d in divisions if 'betterball' not in d['league'].lower()]

        ordered_divisions = betterball_divs + other_divs

        for i, div in enumerate(ordered_divisions):
            print(f"\n[{i+1}/{len(ordered_divisions)}] Checking: {div['season']} - {div['league']} / {div['division']} (ID: {div['division_id']})")

            # Navigate back to seasons page before each check (this also clicks View History)
            self.navigate_to_seasons()
            time.sleep(1)

            # Click Players Results icon - this navigates to a new page
            if self.click_players_results_icon(div['division_id']):
                # First check if Krugersdorp is mentioned on the page
                found, page_text = self.check_page_for_krugersdorp()

                if found:
                    print(f"  *** FOUND KRUGERSDORP! ***")
                    krugersdorp_divisions.append(div)
                else:
                    print(f"  Krugersdorp not found in this division")
            else:
                print(f"  Could not access Players Results")

            time.sleep(1)

        print("\n" + "="*60)
        if krugersdorp_divisions:
            print(f"KRUGERSDORP FOUND IN {len(krugersdorp_divisions)} DIVISIONS:")
            for div in krugersdorp_divisions:
                print(f"  - {div['season']} - {div['league']} / {div['division']} (ID: {div['division_id']})")
        else:
            print("KRUGERSDORP NOT FOUND IN ANY CGGU DIVISION")
            print("The team may be listed under a different name or in a different league.")
        print("="*60)

        return krugersdorp_divisions

    def scrape_division_player_results(self, division_id, player_list):
        """Scrape player results for a specific division

        Returns all Krugersdorp players, with matched_name set if found in player_list,
        or unmatched=True flag if not found (for manual review).
        """
        print(f"\nScraping player results for division {division_id}...")

        all_results = []

        # Navigate to seasons page
        self.navigate_to_seasons()
        time.sleep(2)

        # Click on Players Results icon - this navigates to a new page
        if self.click_players_results_icon(division_id):
            time.sleep(3)  # Wait for page to load

            # Extract results from the page (not a modal)
            results = self.extract_player_results_from_page()

            print(f"  Found {len(results)} player results")

            for result in results:
                # Only include Krugersdorp players
                club = result.get('club', '').lower()
                if 'krugersdorp' not in club and 'kgc' not in club:
                    continue

                matched_name = self.match_player(result['player_name'], player_list)
                if matched_name:
                    result['matched_name'] = matched_name
                    result['unmatched'] = False
                    print(f"    Matched: {result['player_name']} -> {matched_name}")
                else:
                    # Flag unmatched players for manual review
                    result['matched_name'] = result['player_name']  # Use original name
                    result['unmatched'] = True
                    print(f"    UNMATCHED (review needed): {result['player_name']} ({result.get('club', 'Unknown club')})")

                all_results.append(result)

        return all_results

    def extract_player_results_from_page(self):
        """Extract player W/L/D data from the current page"""
        results = []

        try:
            # Wait for content to load
            time.sleep(2)

            # Get all tables on the page
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            print(f"  Found {len(tables)} tables on page")

            for table_idx, table in enumerate(tables):
                try:
                    # Get headers to understand column order
                    headers = []
                    header_row = table.find_elements(By.TAG_NAME, "th")
                    for h in header_row:
                        headers.append(h.text.strip().lower())

                    print(f"  Table {table_idx} headers: {headers}")

                    # Find column indices for the data we need
                    player_col = None
                    played_col = None
                    won_col = None
                    drawn_col = None
                    lost_col = None
                    points_col = None
                    club_col = None
                    team_col = None

                    for i, h in enumerate(headers):
                        if h == 'player':
                            player_col = i
                        elif h == 'played':
                            played_col = i
                        elif h == 'won':
                            won_col = i
                        elif h == 'drawn':
                            drawn_col = i
                        elif h == 'lost':
                            lost_col = i
                        elif h == 'points':
                            points_col = i
                        elif h == 'club':
                            club_col = i
                        elif h == 'team':
                            team_col = i

                    print(f"  Column mapping: player={player_col}, played={played_col}, won={won_col}, drawn={drawn_col}, lost={lost_col}")

                    rows = table.find_elements(By.TAG_NAME, "tr")
                    print(f"  Found {len(rows)} rows")

                    for row_idx, row in enumerate(rows):
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 5:
                            try:
                                # Extract player name
                                player_name = cells[player_col].text.strip() if player_col is not None else cells[1].text.strip()

                                # Skip header-like rows
                                if not player_name or player_name.lower() == 'player':
                                    continue

                                result = {'player_name': player_name}

                                # Extract club and team for context
                                if club_col is not None and club_col < len(cells):
                                    result['club'] = cells[club_col].text.strip()
                                if team_col is not None and team_col < len(cells):
                                    result['team'] = cells[team_col].text.strip()

                                # Extract numeric values
                                if played_col is not None and played_col < len(cells):
                                    val = cells[played_col].text.strip()
                                    result['played'] = int(val) if val.isdigit() else 0
                                if won_col is not None and won_col < len(cells):
                                    val = cells[won_col].text.strip()
                                    result['wins'] = int(val) if val.isdigit() else 0
                                if drawn_col is not None and drawn_col < len(cells):
                                    val = cells[drawn_col].text.strip()
                                    result['draws'] = int(val) if val.isdigit() else 0
                                if lost_col is not None and lost_col < len(cells):
                                    val = cells[lost_col].text.strip()
                                    result['losses'] = int(val) if val.isdigit() else 0
                                if points_col is not None and points_col < len(cells):
                                    val = cells[points_col].text.strip()
                                    try:
                                        result['points'] = float(val) if val else 0
                                    except:
                                        result['points'] = 0

                                results.append(result)
                                print(f"    Row {row_idx}: {player_name} - W:{result.get('wins',0)} L:{result.get('losses',0)} D:{result.get('draws',0)}")

                            except Exception as e:
                                print(f"    Error on row {row_idx}: {e}")
                                continue

                except Exception as e:
                    print(f"  Error processing table {table_idx}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

            # If no tables, try looking for other structures (divs, lists)
            if not results:
                print("  No results from tables, checking other page elements...")
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                print(f"  Page text preview: {body_text[:500]}...")

        except Exception as e:
            print(f"  Error extracting results: {e}")
            import traceback
            traceback.print_exc()

        return results

    def compile_all_results(self, all_division_results, player_list):
        """Compile results from multiple divisions into player records

        Includes all Krugersdorp players, with unmatched flag for those not in player_list.
        """
        records = defaultdict(lambda: {
            'wins': 0, 'losses': 0, 'draws': 0, 'played': 0,
            'divisions': [], 'unmatched': False, 'club': '', 'team': ''
        })

        for div_result in all_division_results:
            division_name = div_result['division']
            season = div_result.get('season', '')

            for result in div_result['results']:
                player = result.get('matched_name', result['player_name'])

                records[player]['wins'] += result.get('wins', 0)
                records[player]['losses'] += result.get('losses', 0)
                records[player]['draws'] += result.get('draws', 0)
                records[player]['played'] += result.get('played', 0)
                records[player]['divisions'].append(f"{season} - {division_name}")
                records[player]['club'] = result.get('club', '')
                records[player]['team'] = result.get('team', '')

                # Track if this player is unmatched (for review)
                if result.get('unmatched', False):
                    records[player]['unmatched'] = True

        return records

    def save_results(self, records, output_file="outputs/matchplay_records.csv"):
        """Save player records to CSV"""
        os.makedirs("outputs", exist_ok=True)

        rows = []
        for player, record in sorted(records.items()):
            # Handle both dict format from compile_all_results and direct format
            wins = record.get('wins', 0)
            losses = record.get('losses', 0)
            draws = record.get('draws', 0)
            played = record.get('played', 0)

            total = wins + losses + draws
            if total == 0:
                total = played

            win_pct = (wins / total * 100) if total > 0 else 0

            divisions = record.get('divisions', [])
            if isinstance(divisions, list):
                divisions = ', '.join(set(divisions))

            club = record.get('club', '')
            team = record.get('team', '')

            unmatched = record.get('unmatched', False)

            rows.append({
                'Player Name': player,
                'Club': club,
                'Team': team,
                'Matches': total,
                'Wins': wins,
                'Losses': losses,
                'Draws': draws,
                'Win %': f"{win_pct:.1f}%",
                'Record': f"{wins}-{losses}-{draws}",
                'Points': record.get('points', 0),
                'Divisions': divisions,
                'Needs Review': 'YES' if unmatched else ''
            })

        if not rows:
            print("\nNo results to save!")
            return None

        df = pd.DataFrame(rows)
        df = df.sort_values('Wins', ascending=False)
        df.to_csv(output_file, index=False)

        print(f"\n{'='*60}")
        print(f"RESULTS SAVED TO {output_file}")
        print(f"{'='*60}")
        print(df.to_string(index=False))

        return df

    def run_full_scan(self, player_list, league_filter='betterball'):
        """Run full scan: find Krugersdorp divisions across all seasons and scrape results

        Args:
            player_list: List of player names to match
            league_filter: Only scan divisions matching this league (default: 'betterball')
        """
        # Navigate and click "View History" to show all seasons
        self.navigate_to_seasons(click_history=True)
        all_divisions = self.get_all_cggu_divisions_info()

        if not all_divisions:
            print("No CGGU divisions found!")
            return None

        # Filter to just the league we care about
        if league_filter:
            filtered_divisions = [d for d in all_divisions if league_filter.lower() in d['league'].lower()]
            print(f"\nFiltered to {len(filtered_divisions)} {league_filter} divisions")
        else:
            filtered_divisions = all_divisions

        # Group by season for better output
        by_season = defaultdict(list)
        for div in filtered_divisions:
            by_season[div['season']].append(div)

        print("\nDivisions by season:")
        for season, divs in sorted(by_season.items()):
            print(f"  {season}: {len(divs)} divisions")

        # Find Krugersdorp divisions by matching players
        krugersdorp_divs = self.scan_for_krugersdorp(filtered_divisions, player_list)

        if not krugersdorp_divs:
            print("\nCould not find Krugersdorp in any division.")
            print("Try running with --no-headless to see what's happening")
            return None

        print(f"\n{'='*60}")
        print(f"SCRAPING PLAYER RESULTS FROM {len(krugersdorp_divs)} KRUGERSDORP DIVISIONS")
        print(f"{'='*60}")

        # Scrape results from each Krugersdorp division
        all_results = []
        for i, div in enumerate(krugersdorp_divs, 1):
            print(f"\n[{i}/{len(krugersdorp_divs)}] Scraping: {div['season']} - {div['league']} / {div['division']}")
            results = self.scrape_division_player_results(div['division_id'], player_list)
            all_results.append({
                'season': div['season'],
                'division': f"{div['league']} / {div['division']}",
                'division_id': div['division_id'],
                'results': results
            })

        # Compile and save
        records = self.compile_all_results(all_results, player_list)
        self.save_results(records)

        return records

    def close(self):
        """Close the browser"""
        try:
            self.driver.quit()
        except:
            pass
        print("\nBrowser closed.")


def main():
    parser = argparse.ArgumentParser(description='Scrape match play results from ScoreCapture')
    parser.add_argument('--no-headless', action='store_true', help='Show browser window')
    parser.add_argument('--division', type=str, help='Specific division ID to scrape')

    args = parser.parse_args()

    headless = not args.no_headless

    scraper = MatchPlayScraper(headless=headless)

    try:
        print("="*60)
        print("SCORECAPTURE MATCH PLAY SCRAPER")
        print("="*60)
        mode = "headless" if headless else "visible browser"
        print(f"Running in {mode} mode\n")

        # Load player list
        player_list = scraper.load_player_list()

        if args.division:
            # Scrape specific division
            scraper.navigate_to_seasons()
            results = scraper.scrape_division_player_results(args.division, player_list)
            records = {r.get('matched_name', r['player_name']): r for r in results}
            scraper.save_results(records)
        else:
            # Full scan
            scraper.run_full_scan(player_list)

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
