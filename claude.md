# Claude Context

## Project Overview
- Project: kgc-league (Krugersdorp Golf Club League)
- Purpose: Track and analyze golf scores for league players
- League format: 16 players total, 8 pairs per match (4 home + 4 away)

## Key Information
- Uses data from handicaps.co.za
- Tracks specific players listed in data/players_list.csv
- Player IDs are SA Player IDs from the handicap system
- Players have different commitment levels: Full, Month-2-month, TBC
- Current player pool: 31 players (sorted alphabetically by first name)

## Data Files
- **data/players_list.csv**: List of 31 players with their Player IDs and commitment levels
  - Columns: Name, Player ID, Commitment
  - Sorted alphabetically by first name

## Scripts

### golf_scraper.py
Web scraper to retrieve player score history and current handicap info
- Scrapes from handicaps.co.za for Krugersdorp Golf Club
- Searches for each player individually by SA Player ID (optimized approach)
- Runs in headless mode by default (no browser window)
- Reads player list from data/players_list.csv
- **Outputs two files:**
  - `outputs/scores.csv` - Score history with columns:
    - Player Name, SA Player ID, Date Played, Club Played, Tee, Tee Color, CR, SLOPE, OPEN HI, CH, GROSS, DIFF
  - `outputs/players_info.csv` - Player info with columns:
    - Player Name, SA Player ID, Current HI
- Usage: `python3 golf_scraper.py`
- The outputs folder is created automatically if it doesn't exist
- To see the browser window, edit line 384 and change `headless=True` to `headless=False`

### analyze_scores.py
Analyzes player performance and generates comprehensive metrics
- Input: outputs/scores.csv
- Output: outputs/analysis.csv (contains blended Combined Value Score)
- Analysis period: Last 12 weeks
- Usage: `python3 analyze_scores.py`

**Blended Scoring (70% HOME + 30% ALL):**
- Calculates metrics for both ALL rounds and HOME-only rounds
- Final Combined Value Score is blended: `0.7 × HOME_CVS + 0.3 × ALL_CVS`
- This reduces the impact of bad away rounds (e.g., vacation golf) while still accounting for overall performance
- HOME-only columns are prefixed with `HOME_` for reference
- Original ALL score saved as `ALL_Combined Value Score` for comparison

**Key Metrics Calculated:**
1. **Basic Stats**: Total rounds, avg rounds per week, home games %
2. **Performance Metrics**: Avg DIFF - OPEN HI (ALL, HOME, AWAY)
3. **Trend Analysis**: Recent 6 weeks vs oldest 6 weeks with confidence weighting
4. **Consistency**: Standard deviation (ALL, HOME, AWAY)
5. **Player Type**: Steady (StdDev < 2.5) vs Explosive (StdDev >= 2.5)
6. **Volatility Index**: Overall standard deviation
7. **Coefficient of Variation**: StdDev / Mean (normalized volatility)

**Classification System:**
All ratings use **team distribution-based thresholds** (percentiles) rather than fixed values.
This means thresholds adjust dynamically based on the current player pool.

- **Performance Rating**: Based on Avg DIFF - OPEN HI (lower is better)
  - Thresholds calculated from team percentiles:
    - Excellent: Bottom 20% (best performers)
    - Good: 20-40%
    - Average: 40-60%
    - Below Average: 60-80%
    - Poor: Top 20% (worst performers)
  - Scores: 10, 8, 6, 4, 2

- **Trend Rating**: Based on weighted trend change (recent 6w vs oldest 6w)
  - Weighted by confidence: `trend_change = raw_change × confidence`
  - Confidence = min(rounds_recent, rounds_oldest) / max(rounds_recent, rounds_oldest)
  - This dampens trend when round counts are imbalanced (e.g., 2 rounds vs 10 rounds)
  - Thresholds calculated from team percentiles (lower = better/improving):
    - Improving Strongly: Bottom 20% (most improved)
    - Improving: 20-40%
    - Stable: 40-60%
    - Declining: 60-80%
    - Declining Strongly: Top 20% (most declined)
  - Scores: 10, 8, 6, 4, 2

- **Consistency Rating**: Based on pure StdDev (standard deviation of DIFF - OPEN HI)
  - Thresholds calculated from team percentiles:
    - Very Consistent: Bottom 20% (most consistent)
    - Consistent: 20-40%
    - Moderately Consistent: 40-60%
    - Variable: 60-80%
    - Very Variable: Top 20% (least consistent)
  - Scores: 10, 8, 6, 4, 2

- **Role**: Based on Handicap Index + Consistency (for pairing strategy)
  - Uses median Handicap Index as threshold for high/low
  - **Anchor**: Low handicap (< median HI) + Good consistency (score >= 6)
    - Reliable low-handicappers who won't blow up
  - **Gunner**: High handicap (>= median HI) + Good consistency (score >= 6)
    - Consistently deliver their strokes - valuable for match play
  - **Wildcard**: Poor consistency (score < 6) regardless of handicap
    - Unpredictable players, can fill either role as needed

- **Player Type (Steady vs Explosive)**: Based on median Adjusted StdDev
  - Adjusted StdDev = StdDev + (Handicap Index × 0.10)
  - Steady: Below median (consistent round-to-round)
  - Explosive: Above median (variable scores)

- **Combined Value Score**: Weighted average
  - Performance: 60%
  - Consistency: 30%
  - Trend: 10%
  - Used for overall player ranking

- **Preferred Location**: HOME, AWAY, or ANY
  - Based on performance gap between home and away (minimum 3 rounds each location)
  - HOME (Strong): Away diff - Home diff > 1.0 (performs much better at home)
  - HOME: 0.5 to 1.0 advantage
  - ANY: -0.5 to 0.5 (no significant difference)
  - AWAY: -1.0 to -0.5 advantage
  - AWAY (Strong): < -1.0 (performs much better away)
  - Also flags limited data scenarios

**Understanding the Metrics:**
- DIFF - OPEN HI: How many strokes over/under handicap (lower is better)
- Adjusted StdDev: Raw StdDev + (Handicap × 0.10) - used for Player Type classification
- HOME = KRUGERSDORP GOLF CLUB, AWAY = all other courses
- Anchor: Low handicap + consistent - reliable foundation for pairing
- Gunner: High handicap + consistent - reliably delivers strokes in match play
- Wildcard: Inconsistent regardless of handicap - unpredictable, use flexibly

### generate_dashboard.py
Creates interactive HTML dashboard for visual analysis
- Input: outputs/analysis.csv (contains blended Combined Value Score)
- Output: outputs/dashboard.html
- Usage: `python3 generate_dashboard.py`

**Dashboard Features:**
- Uses blended scores (70% HOME + 30% ALL) for ranking
- Interactive player cards with all metrics
- Filter options:
  - All Players
  - Excellent (Score >= 8)
  - Good (Score >= 6)
  - Anchors (low HC + consistent)
  - Wildcards (inconsistent)
  - Gunners (high HC + consistent)
  - Home Preference
  - Away Preference
- Color-coded scores (Excellent=green, Good=blue, Average=orange, Below=red)
- Role badges showing player role (Anchor/Gunner/Wildcard)
- Location badges showing preferred playing location
- Player count display showing filtered results

### generate_pairings.py
Generates optimized team pairings using Anchor + Gunner strategy
- Input: outputs/analysis.csv, outputs/scores.csv
- Output: outputs/pairings.csv
- Usage: `python3 generate_pairings.py`

**Pairing Strategy:**
1. Select top 8 Anchor players by Combined Value Score
2. Select top 8 Gunner players by Combined Value Score
3. Wildcard players can fill either role as needed
4. Use optimization to pair anchors with gunners

**Constraints:**
- Required pairings: Greg Park + Hugo Lamprecht
- Either/or: Ian Scott OR Grant Syme + Matt Maritz
- Exclusions: Jacques vd Berg cannot pair with Gerdus Theron, Frank Coetzee, or Marcelle Smith
- Minimum CH difference: 2 strokes between paired players (for handicap balance)

**Optimization:**
- Uses permutation search to find optimal valid assignment
- Maximizes total combined score while respecting all constraints
- Falls back to greedy assignment if no valid solution found

**Output includes:**
- Pair number and constraint type (REQUIRED, AUTO)
- Anchor and Gunner names with Combined Value Scores
- Course Handicap (CH) for each player at Krugersdorp
- CH difference between paired players
- Performance ratings and preferred locations
- Location recommendations (HOME/AWAY/Flexible)
- Reserve players list

## Team Selection Strategy

**Two-Step Approach:**
1. **Team Selection**: Use Combined Value Score to select top 16 players from pool of 26
2. **Pairing Strategy**: Use individual Performance, Trend, and Consistency ratings

**Pairing Philosophy:**
- Anchor + Gunner approach for match play
- Anchors: Low handicap + consistent players (reliable foundation)
- Gunners: High handicap + consistent players (reliably deliver strokes)
- Wildcards: Inconsistent players used flexibly to fill gaps

**Location Assignment Strategy:**
- Assign players with strong HOME preference to the 4 home pairs
- Assign players with strong AWAY preference to the 4 away pairs
- Use flexible (ANY) players to fill remaining spots

**Top Performers (Combined Value Score >= 7.0):**
- Jacques vd Berg: 10.0 (Excellent/Improving Strongly/Very Consistent) - Gunner, HOME (Strong)
- Pieter de la Rey: 10.0 (Excellent/Improving Strongly/Very Consistent) - Anchor, HOME
- Grant Syme: 8.8 (Excellent/Stable/Very Consistent) - Anchor
- Greg Park: 8.2 (Excellent/Declining/Very Consistent) - Anchor, ANY
- Ian Scott: 8.0 (Good/Improving Strongly/Moderately Consistent) - Anchor, HOME
- Brandon Bester: 7.8 (Average/Improving Strongly/Consistent) - Anchor, HOME (Strong)
- Mario van der Merwe: 7.6 (Excellent/Declining Strongly/Very Consistent) - Anchor, HOME
- Marcelle Smith: 7.4 (Good/Stable/Consistent) - Gunner, HOME (Strong)
- Frank Coetzee: 7.2 (Average/Improving Strongly/Moderately Consistent) - Gunner, HOME
- Bennie Knoetze: 7.0 (Excellent/Declining Strongly/Consistent) - Anchor, AWAY (Strong)

**Role Distribution:**
- Anchors: 12 players (low HC + consistent)
- Gunners: 6 players (high HC + consistent)
- Wildcards: 12 players (inconsistent)

**Notable Location Preferences:**
- Strong HOME players: Corne van Tonder (+4.68), Pieter Viljoen (+4.29), Jacques vd Berg (+2.88)
- Strong AWAY players: Craig Johnson (-5.10), Gerdus Theron (-3.35), Bennie Knoetze (-1.67)

## Workflow

1. **Update player list** (if needed): Edit data/players_list.csv
2. **Scrape latest scores**: `python3 golf_scraper.py`
   - Outputs: outputs/scores.csv, outputs/players_info.csv
3. **Run analysis**: `python3 analyze_scores.py`
4. **Generate dashboard**: `python3 generate_dashboard.py`
5. **Generate pairings**: `python3 generate_pairings.py`
6. **View dashboard**: Open outputs/dashboard.html in browser
7. **Review outputs**:
   - outputs/players_info.csv - Current HI for each player
   - outputs/scores.csv - Raw score history
   - outputs/analysis.csv - Detailed player metrics
   - outputs/pairings.csv - Team pairings with CH balance

## Important Notes

- DIFF values in raw data have 'c' suffix that gets cleaned during analysis
- OPEN HI values may have 'S' suffix (soft cap indicator) that gets cleaned during analysis
- Date format in raw data: '%d-%m-%Y %p'
- Analysis uses rolling 12-week window from current date
- Combined Value Score only calculated for players with complete data (all three ratings available)
- Location preference requires minimum 3 rounds at each location for comparison
- Dashboard automatically filters to players with valid Combined Value Scores
- Course Handicap (CH) is extracted from the latest Krugersdorp round for each player