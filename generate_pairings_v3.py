"""
KGC League Pairings Generator v3
================================
Fresh start - no constraints, super-strong committed home team.

Strategy:
1. Select top 16 players (committed first, then month-to-month)
2. Split into Anchors (low HI) and Gunners (high HI)
3. Pair best Anchor with best Gunner for strongest pairs
4. Top 4 pairs = HOME team (players must have sufficient home rounds)
5. Bottom 4 pairs = AWAY team

Constraints:
- Players with insufficient home rounds (<5) are AWAY-only
"""

import pandas as pd
from itertools import combinations
import os

# Players who cannot play HOME (insufficient home course experience)
AWAY_ONLY_PLAYERS = [
    'Werner van Loggerenburg',  # Only 1 home round out of 43 total
]

# Players on the bench (not in any pair, reserve only)
BENCH_PLAYERS = [
    'Werner van Loggerenburg',  # On bench - only 1 home round
]

# Minimum home rounds required for HOME team eligibility
MIN_HOME_ROUNDS = 5

# Required pairings (must be together)
REQUIRED_PAIRINGS = [
    ('Greg Park', 'Hugo Lamprecht'),
    ('Jacques vd Berg', 'Brandon Bester'),
    ('Ian Scott', 'Matt Maritz'),
]


def load_data():
    """Load all required data files"""

    # Load analysis (includes HOME_Total Rounds)
    analysis = pd.read_csv('outputs/analysis.csv')

    # Load player list for commitments
    players = pd.read_csv('data/players_list.csv')
    commitment_map = dict(zip(players['Name'], players['Commitmnet'].str.strip()))

    # Load matchplay records
    matchplay_map = {}
    if os.path.exists('outputs/matchplay_records.csv'):
        mp = pd.read_csv('outputs/matchplay_records.csv')
        for _, row in mp.iterrows():
            matchplay_map[row['Player Name']] = {
                'wins': row['Wins'],
                'losses': row['Losses'],
                'draws': row['Draws'],
                'matches': row['Matches'],
                'win_pct': float(row['Win %'].replace('%', '')) if pd.notna(row['Win %']) else 0,
                'record': row['Record']
            }

    # Load current HI from players_info
    hi_map = {}
    if os.path.exists('outputs/players_info.csv'):
        info = pd.read_csv('outputs/players_info.csv')
        for _, row in info.iterrows():
            if pd.notna(row.get('Current HI')):
                hi_map[row['Player Name']] = float(row['Current HI'])

    return analysis, commitment_map, matchplay_map, hi_map


def get_player_data(name, analysis_df, commitment_map, matchplay_map, hi_map):
    """Get all relevant data for a player"""
    player = {'name': name}

    # Get analysis data
    row = analysis_df[analysis_df['Player Name'] == name]
    if not row.empty:
        row = row.iloc[0]
        player['cvs'] = row.get('Combined Value Score')
        player['role'] = row.get('Role', 'Unknown')
        player['performance'] = row.get('Performance Rating', 'Unknown')
        player['trend'] = row.get('Trend Rating', 'Unknown')
        player['consistency'] = row.get('Consistency Rating', 'Unknown')

        # Calculate home rounds from Total Rounds and Home Games %
        total_rounds = row.get('Total Rounds (12 weeks)', 0) or 0
        home_pct = row.get('Home Games %', 0) or 0
        player['total_rounds'] = int(total_rounds)
        player['home_rounds'] = int(round(total_rounds * home_pct / 100)) if home_pct > 0 else 0
    else:
        player['cvs'] = None
        player['role'] = 'Unknown'
        player['performance'] = 'Unknown'
        player['trend'] = 'Unknown'
        player['consistency'] = 'Unknown'
        player['home_rounds'] = 0
        player['total_rounds'] = 0

    # Get commitment
    player['commitment'] = commitment_map.get(name, 'Unknown')

    # Get matchplay record
    player['matchplay'] = matchplay_map.get(name)

    # Get handicap index
    player['hi'] = hi_map.get(name, 15)  # Default 15 if unknown

    # Check if player can play HOME
    player['can_play_home'] = (
        name not in AWAY_ONLY_PLAYERS and
        player['home_rounds'] >= MIN_HOME_ROUNDS
    )

    return player


def generate_pairings():
    """Generate optimal pairings - Anchor + Gunner style, committed home team"""

    print("=" * 70)
    print("KGC LEAGUE PAIRINGS v3 - SUPER STRONG HOME TEAM")
    print("=" * 70)
    print("\nStrategy:")
    print("  - Anchor (low HI) + Gunner (high HI) pairings")
    print("  - Committed players prioritized for HOME team")
    print("  - Players need sufficient home rounds for HOME eligibility")
    print(f"\nConstraints:")
    print(f"  - AWAY-only players: {', '.join(AWAY_ONLY_PLAYERS)}")
    print(f"  - Bench players (reserve only): {', '.join(BENCH_PLAYERS)}")
    print(f"  - Minimum home rounds for HOME: {MIN_HOME_ROUNDS}")

    # Load data
    analysis, commitment_map, matchplay_map, hi_map = load_data()

    # Get all players with data
    all_players = []
    for name in commitment_map.keys():
        player = get_player_data(name, analysis, commitment_map, matchplay_map, hi_map)
        if player['cvs'] is not None:
            all_players.append(player)

    # Sort by CVS
    all_players.sort(key=lambda p: p['cvs'] or 0, reverse=True)

    # Separate committed vs month-to-month (excluding bench players from selection)
    committed = [p for p in all_players if p['commitment'] == 'Full' and p['name'] not in BENCH_PLAYERS]
    monthly = [p for p in all_players if p['commitment'] == 'Month-2-month' and p['name'] not in BENCH_PLAYERS]
    tbc = [p for p in all_players if p['commitment'] == 'TBC' and p['name'] not in BENCH_PLAYERS]

    print(f"\nAvailable players (excluding bench):")
    print(f"  Committed (Full): {len(committed)}")
    print(f"  Month-to-month: {len(monthly)}")
    print(f"  TBC: {len(tbc)}")

    # Flag players who can't play HOME
    away_only = [p for p in all_players if not p['can_play_home'] and p['name'] not in BENCH_PLAYERS]
    if away_only:
        print(f"\nAWAY-only players (insufficient home rounds):")
        for p in away_only:
            print(f"  - {p['name']}: {p['home_rounds']} home rounds out of {p['total_rounds']} total")

    # We need 16 players for 8 pairs
    # Take all committed first, then fill with monthly
    selected = []
    selected.extend(committed)

    remaining_needed = 16 - len(selected)
    if remaining_needed > 0:
        selected.extend(monthly[:remaining_needed])

    remaining_needed = 16 - len(selected)
    if remaining_needed > 0:
        selected.extend(tbc[:remaining_needed])

    print(f"\nSelected 16 players for pairings:")
    print(f"  Committed: {len([p for p in selected if p['commitment'] == 'Full'])}")
    print(f"  Month-to-month: {len([p for p in selected if p['commitment'] == 'Month-2-month'])}")
    print(f"  HOME eligible: {len([p for p in selected if p['can_play_home']])}")
    print(f"  AWAY only: {len([p for p in selected if not p['can_play_home']])}")

    # Split into Anchors (low HI) and Gunners (high HI) using median
    selected.sort(key=lambda p: p['hi'])
    median_hi = selected[len(selected) // 2]['hi']

    anchors = [p for p in selected if p['hi'] < median_hi]
    gunners = [p for p in selected if p['hi'] >= median_hi]

    # Balance if needed
    while len(anchors) > 8:
        # Move lowest CVS anchor to gunners
        anchors.sort(key=lambda p: p['cvs'] or 0)
        gunners.append(anchors.pop(0))
    while len(gunners) > 8:
        # Move lowest CVS gunner to anchors
        gunners.sort(key=lambda p: p['cvs'] or 0)
        anchors.append(gunners.pop(0))

    # Sort each by CVS descending
    anchors.sort(key=lambda p: p['cvs'] or 0, reverse=True)
    gunners.sort(key=lambda p: p['cvs'] or 0, reverse=True)

    print(f"\n{'=' * 70}")
    print("ANCHORS (Low HI) - Sorted by CVS")
    print(f"{'=' * 70}")
    for i, p in enumerate(anchors, 1):
        mp = p['matchplay']
        mp_str = f"{mp['record']}" if mp else "New"
        print(f"  {i}. {p['name']:<22} HI={p['hi']:>5.1f}  CVS={p['cvs']:>5.1f}  MP={mp_str:<12} {p['commitment']}")

    print(f"\n{'=' * 70}")
    print("GUNNERS (High HI) - Sorted by CVS")
    print(f"{'=' * 70}")
    for i, p in enumerate(gunners, 1):
        mp = p['matchplay']
        mp_str = f"{mp['record']}" if mp else "New"
        print(f"  {i}. {p['name']:<22} HI={p['hi']:>5.1f}  CVS={p['cvs']:>5.1f}  MP={mp_str:<12} {p['commitment']}")

    # Create pairings: Best Anchor with Best Gunner
    print(f"\n{'=' * 70}")
    print("GENERATING PAIRINGS (Best Anchor + Best Gunner)")
    print(f"{'=' * 70}")

    # Helper to find player by name
    def find_player(name, player_list):
        for p in player_list:
            if p['name'] == name:
                return p
        return None

    # Helper to create a pairing dict
    def make_pairing(anchor, gunner, constraint_type="AUTO"):
        pair_cvs = (anchor['cvs'] or 0) + (gunner['cvs'] or 0)
        hi_spread = abs(anchor['hi'] - gunner['hi'])
        committed_count = sum(1 for p in [anchor, gunner] if p['commitment'] == 'Full')
        can_play_home = anchor['can_play_home'] and gunner['can_play_home']
        return {
            'anchor': anchor,
            'gunner': gunner,
            'pair_cvs': pair_cvs,
            'hi_spread': hi_spread,
            'committed_count': committed_count,
            'can_play_home': can_play_home,
            'constraint': constraint_type
        }

    pairings = []
    used_players = set()

    # First, handle required pairings
    if REQUIRED_PAIRINGS:
        print("\nApplying required pairings...")
        for name1, name2 in REQUIRED_PAIRINGS:
            p1 = find_player(name1, selected)
            p2 = find_player(name2, selected)

            if p1 and p2:
                # Determine which is anchor (lower HI) and which is gunner (higher HI)
                if p1['hi'] < p2['hi']:
                    anchor, gunner = p1, p2
                else:
                    anchor, gunner = p2, p1

                pairings.append(make_pairing(anchor, gunner, "REQUIRED"))
                used_players.add(anchor['name'])
                used_players.add(gunner['name'])
                print(f"  REQUIRED: {anchor['name']} (HI={anchor['hi']:.1f}) + {gunner['name']} (HI={gunner['hi']:.1f})")
            else:
                missing = name1 if not p1 else name2
                print(f"  WARNING: Could not find {missing} for required pairing")

    # Get remaining players (not used in required pairings)
    remaining = [p for p in selected if p['name'] not in used_players]

    # Re-split into anchors and gunners from remaining players
    remaining.sort(key=lambda p: p['hi'])
    mid = len(remaining) // 2
    anchors = remaining[:mid]
    gunners = remaining[mid:]

    # Sort by CVS
    anchors.sort(key=lambda p: p['cvs'] or 0, reverse=True)
    gunners.sort(key=lambda p: p['cvs'] or 0, reverse=True)

    print(f"\nAfter required pairings: {len(anchors)} anchors, {len(gunners)} gunners available")

    # Fill remaining pairs with best anchor + best gunner
    remaining_pairs = 8 - len(pairings)
    for i in range(remaining_pairs):
        if i < len(anchors) and i < len(gunners):
            anchor = anchors[i]
            gunner = gunners[i]
            pairings.append(make_pairing(anchor, gunner, "AUTO"))

    # Sort pairings: HOME-eligible pairs first (by CVS), then AWAY-only pairs (by CVS)
    home_eligible = [p for p in pairings if p['can_play_home']]
    away_only_pairs = [p for p in pairings if not p['can_play_home']]

    home_eligible.sort(key=lambda p: p['pair_cvs'], reverse=True)
    away_only_pairs.sort(key=lambda p: p['pair_cvs'], reverse=True)

    # Take top 4 HOME-eligible for HOME, rest go AWAY
    # AWAY-only pairs must go to AWAY slots
    pairings = home_eligible[:4] + away_only_pairs + home_eligible[4:]

    # Assign HOME (1-4) and AWAY (5-8)
    print(f"\n{'=' * 70}")
    print("FINAL PAIRINGS")
    print(f"{'=' * 70}")

    rows = []
    for i, pair in enumerate(pairings, 1):
        location = "HOME" if i <= 4 else "AWAY"
        anchor = pair['anchor']
        gunner = pair['gunner']

        anchor_mp = anchor['matchplay']
        gunner_mp = gunner['matchplay']
        anchor_mp_str = anchor_mp['record'] if anchor_mp else "New"
        gunner_mp_str = gunner_mp['record'] if gunner_mp else "New"

        # Show constraint and home eligibility notes
        constraint = pair.get('constraint', 'AUTO')
        constraint_note = f" [{constraint}]" if constraint != "AUTO" else ""

        home_note = ""
        if not pair['can_play_home']:
            if not anchor['can_play_home']:
                home_note = f" [!{anchor['name']} AWAY-only]"
            if not gunner['can_play_home']:
                home_note = f" [!{gunner['name']} AWAY-only]"

        print(f"\nPair {i} ({location}){constraint_note}{home_note}:")
        print(f"  Anchor: {anchor['name']:<20} HI={anchor['hi']:>5.1f}  CVS={anchor['cvs']:>5.1f}  MP={anchor_mp_str}  {anchor['commitment']}  HR={anchor['home_rounds']}")
        print(f"  Gunner: {gunner['name']:<20} HI={gunner['hi']:>5.1f}  CVS={gunner['cvs']:>5.1f}  MP={gunner_mp_str}  {gunner['commitment']}  HR={gunner['home_rounds']}")
        print(f"  Combined CVS: {pair['pair_cvs']:.1f}  |  HI Spread: {pair['hi_spread']:.1f}")

        rows.append({
            'Pair': i,
            'Location': location,
            'Pair CVS': round(pair['pair_cvs'], 2),
            'Anchor': anchor['name'],
            'Anchor HI': anchor['hi'],
            'Anchor CVS': anchor['cvs'],
            'Anchor MP': anchor_mp_str,
            'Anchor Commitment': anchor['commitment'],
            'Anchor Home Rounds': anchor['home_rounds'],
            'Gunner': gunner['name'],
            'Gunner HI': gunner['hi'],
            'Gunner CVS': gunner['cvs'],
            'Gunner MP': gunner_mp_str,
            'Gunner Commitment': gunner['commitment'],
            'Gunner Home Rounds': gunner['home_rounds'],
            'HI Spread': round(pair['hi_spread'], 1)
        })

    # Save to CSV
    df = pd.DataFrame(rows)
    output_file = 'outputs/pairings_v3.csv'
    df.to_csv(output_file, index=False)

    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")

    home_pairs = [p for p in pairings[:4]]
    away_pairs = [p for p in pairings[4:]]

    home_cvs = sum(p['pair_cvs'] for p in home_pairs)
    away_cvs = sum(p['pair_cvs'] for p in away_pairs)

    home_committed = sum(p['committed_count'] for p in home_pairs)
    away_committed = sum(p['committed_count'] for p in away_pairs)

    print(f"\nHOME Team (Pairs 1-4):")
    print(f"  Total CVS: {home_cvs:.1f}")
    print(f"  Committed players: {home_committed}/8")

    print(f"\nAWAY Team (Pairs 5-8):")
    print(f"  Total CVS: {away_cvs:.1f}")
    print(f"  Committed players: {away_committed}/8")

    # Show reserves/substitutes
    print(f"\n{'=' * 70}")
    print("RESERVES / SUBSTITUTES")
    print(f"{'=' * 70}")

    # Get players not selected
    selected_names = set()
    for pair in pairings:
        selected_names.add(pair['anchor']['name'])
        selected_names.add(pair['gunner']['name'])

    reserves = [p for p in all_players if p['name'] not in selected_names]
    reserves.sort(key=lambda p: p['cvs'] or 0, reverse=True)

    for i, p in enumerate(reserves[:6], 1):
        mp = p['matchplay']
        mp_str = mp['record'] if mp else "New"
        home_status = "HOME OK" if p['can_play_home'] else "AWAY ONLY"
        print(f"  {i}. {p['name']:<22} CVS={p['cvs']:>5.1f}  HI={p['hi']:>5.1f}  MP={mp_str:<12} {p['commitment']:<15} {home_status}")

    print(f"\nPairings saved to: {output_file}")

    return pairings, all_players


if __name__ == "__main__":
    generate_pairings()
