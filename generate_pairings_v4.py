"""
KGC League Pairings Generator v4
================================
New Strategy: Best Anchors with Wildcards, Mid Anchors with Gunners

Philosophy:
- Top anchors (best CVS) can "carry" unpredictable wildcards - high upside potential
- Mid anchors need consistent gunner partners to stay competitive

Strategy:
1. Select top 16 players (committed first, then month-to-month)
2. Split into Anchors (low HI) - 8 players
3. Split anchors into TOP 4 (best CVS) and MID 4 (lower CVS)
4. Split high HI players into Gunners (consistent) and Wildcards (inconsistent)
5. Pair: TOP Anchors + Wildcards, MID Anchors + Gunners
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

# Required pairings (must be together) - empty for fresh start
REQUIRED_PAIRINGS = []


def load_data():
    """Load all required data files"""

    # Load analysis (includes HOME_Total Rounds)
    analysis = pd.read_csv('outputs/analysis.csv')

    # Load player list for commitments
    players = pd.read_csv('data/players_list.csv')
    commitment_map = dict(zip(players['Name'], players['Commitmnet'].str.strip()))

    # Load matchplay records
    matchplay_map = {}
    matchplay_file = 'outputs/matchplay_records.csv'
    if os.path.exists(matchplay_file):
        mp_df = pd.read_csv(matchplay_file)
        for _, row in mp_df.iterrows():
            matchplay_map[row['Player Name']] = {
                'wins': row['Wins'],
                'losses': row['Losses'],
                'draws': row['Draws'],
                'matches': row['Matches'],
                'win_pct': float(row['Win %'].replace('%', '')) if isinstance(row['Win %'], str) else row['Win %'],
                'record': row['Record']
            }

    # Load player handicaps
    hi_map = {}
    players_info_file = 'outputs/players_info.csv'
    if os.path.exists(players_info_file):
        pi_df = pd.read_csv(players_info_file)
        for _, row in pi_df.iterrows():
            hi_map[row['Player Name']] = row['Current HI']

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
        player['consistency_score'] = row.get('Consistency Score', 0)

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
        player['consistency_score'] = 0
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

    # Determine if player is a wildcard (inconsistent)
    # Use consistency score - lower score = less consistent = wildcard
    player['is_wildcard'] = player['consistency_score'] < 6 if player['consistency_score'] else False

    return player


def generate_pairings():
    """Generate optimal pairings - Best Anchors + Wildcards, Mid Anchors + Gunners"""

    print("=" * 70)
    print("KGC LEAGUE PAIRINGS v4 - ANCHORS + WILDCARDS/GUNNERS STRATEGY")
    print("=" * 70)
    print("\nStrategy:")
    print("  - TOP Anchors (best CVS) + Wildcards (high upside potential)")
    print("  - MID Anchors (solid) + Gunners (consistent stroke delivery)")
    print("  - Committed players prioritized for HOME team")
    print(f"\nConstraints:")
    print(f"  - AWAY-only players: {', '.join(AWAY_ONLY_PLAYERS) if AWAY_ONLY_PLAYERS else 'None'}")
    print(f"  - Bench players (reserve only): {', '.join(BENCH_PLAYERS) if BENCH_PLAYERS else 'None'}")
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

    # Split into Anchors (low HI) and High HI players using median
    selected.sort(key=lambda p: p['hi'])
    mid = len(selected) // 2

    anchors = selected[:mid]  # Lower HI = Anchors
    high_hi_players = selected[mid:]  # Higher HI

    # Sort anchors by CVS to split into TOP and MID
    anchors.sort(key=lambda p: p['cvs'] or 0, reverse=True)
    top_anchors = anchors[:4]
    mid_anchors = anchors[4:]

    # Split high HI players into Gunners (consistent) and Wildcards (inconsistent)
    gunners = [p for p in high_hi_players if not p['is_wildcard']]
    wildcards = [p for p in high_hi_players if p['is_wildcard']]

    # Sort each by CVS
    gunners.sort(key=lambda p: p['cvs'] or 0, reverse=True)
    wildcards.sort(key=lambda p: p['cvs'] or 0, reverse=True)

    print(f"\n{'=' * 70}")
    print("PLAYER CLASSIFICATION")
    print(f"{'=' * 70}")

    print(f"\nTOP ANCHORS (Best 4 low HI by CVS) - will pair with Wildcards:")
    for i, p in enumerate(top_anchors, 1):
        mp = p['matchplay']
        mp_str = f"{mp['record']}" if mp else "New"
        print(f"  {i}. {p['name']:<22} HI={p['hi']:>5.1f}  CVS={p['cvs']:>5.1f}  Cons={p['consistency_score'] or 0:>3}  MP={mp_str:<12} {p['commitment']}")

    print(f"\nMID ANCHORS (Lower 4 low HI by CVS) - will pair with Gunners:")
    for i, p in enumerate(mid_anchors, 1):
        mp = p['matchplay']
        mp_str = f"{mp['record']}" if mp else "New"
        print(f"  {i}. {p['name']:<22} HI={p['hi']:>5.1f}  CVS={p['cvs']:>5.1f}  Cons={p['consistency_score'] or 0:>3}  MP={mp_str:<12} {p['commitment']}")

    print(f"\nGUNNERS (High HI + Consistent) - will pair with Mid Anchors:")
    for i, p in enumerate(gunners, 1):
        mp = p['matchplay']
        mp_str = f"{mp['record']}" if mp else "New"
        wc = "WC" if p['is_wildcard'] else ""
        print(f"  {i}. {p['name']:<22} HI={p['hi']:>5.1f}  CVS={p['cvs']:>5.1f}  Cons={p['consistency_score'] or 0:>3}  MP={mp_str:<12} {p['commitment']} {wc}")

    print(f"\nWILDCARDS (High HI + Inconsistent) - will pair with Top Anchors:")
    for i, p in enumerate(wildcards, 1):
        mp = p['matchplay']
        mp_str = f"{mp['record']}" if mp else "New"
        print(f"  {i}. {p['name']:<22} HI={p['hi']:>5.1f}  CVS={p['cvs']:>5.1f}  Cons={p['consistency_score'] or 0:>3}  MP={mp_str:<12} {p['commitment']}")

    # Check if we have enough players in each category
    print(f"\nPlayer counts: Top Anchors={len(top_anchors)}, Mid Anchors={len(mid_anchors)}, Gunners={len(gunners)}, Wildcards={len(wildcards)}")

    # We need 4 wildcards for top anchors and 4 gunners for mid anchors
    # If we don't have enough wildcards, use gunners for top anchors too
    # If we don't have enough gunners, use wildcards for mid anchors

    # Combine and redistribute if needed
    all_high_hi = gunners + wildcards
    all_high_hi.sort(key=lambda p: p['cvs'] or 0, reverse=True)

    # Helper to create a pairing dict
    def make_pairing(anchor, partner, pairing_type="AUTO"):
        pair_cvs = (anchor['cvs'] or 0) + (partner['cvs'] or 0)
        hi_spread = abs(anchor['hi'] - partner['hi'])
        committed_count = sum(1 for p in [anchor, partner] if p['commitment'] == 'Full')
        can_play_home = anchor['can_play_home'] and partner['can_play_home']
        return {
            'anchor': anchor,
            'gunner': partner,  # Keep 'gunner' key for compatibility
            'pair_cvs': pair_cvs,
            'hi_spread': hi_spread,
            'committed_count': committed_count,
            'can_play_home': can_play_home,
            'pairing_type': pairing_type
        }

    pairings = []
    used_players = set()

    print(f"\n{'=' * 70}")
    print("GENERATING PAIRINGS")
    print(f"{'=' * 70}")

    # Strategy: Top anchors get wildcards (or best available high-upside players)
    # Mid anchors get gunners (consistent players)

    print("\nPairing TOP Anchors with best Wildcards/High-upside players...")
    for anchor in top_anchors:
        # Find best available wildcard first, then any high HI player
        best_partner = None
        for p in wildcards:
            if p['name'] not in used_players:
                best_partner = p
                break

        # If no wildcard available, use best available high HI player
        if not best_partner:
            for p in all_high_hi:
                if p['name'] not in used_players:
                    best_partner = p
                    break

        if best_partner:
            pairings.append(make_pairing(anchor, best_partner, "TOP+WILDCARD"))
            used_players.add(anchor['name'])
            used_players.add(best_partner['name'])
            wc_label = "(Wildcard)" if best_partner['is_wildcard'] else "(Gunner)"
            print(f"  {anchor['name']} (HI={anchor['hi']:.1f}, CVS={anchor['cvs']:.1f}) + {best_partner['name']} {wc_label} (HI={best_partner['hi']:.1f}, CVS={best_partner['cvs']:.1f})")

    print("\nPairing MID Anchors with best Gunners/Consistent players...")
    for anchor in mid_anchors:
        # Find best available gunner first, then any high HI player
        best_partner = None
        for p in gunners:
            if p['name'] not in used_players:
                best_partner = p
                break

        # If no gunner available, use best available high HI player
        if not best_partner:
            for p in all_high_hi:
                if p['name'] not in used_players:
                    best_partner = p
                    break

        if best_partner:
            pairings.append(make_pairing(anchor, best_partner, "MID+GUNNER"))
            used_players.add(anchor['name'])
            used_players.add(best_partner['name'])
            wc_label = "(Wildcard)" if best_partner['is_wildcard'] else "(Gunner)"
            print(f"  {anchor['name']} (HI={anchor['hi']:.1f}, CVS={anchor['cvs']:.1f}) + {best_partner['name']} {wc_label} (HI={best_partner['hi']:.1f}, CVS={best_partner['cvs']:.1f})")

    # Sort pairings: HOME-eligible pairs first (by CVS), then AWAY-only pairs (by CVS)
    home_eligible = [p for p in pairings if p['can_play_home']]
    away_only_pairs = [p for p in pairings if not p['can_play_home']]

    home_eligible.sort(key=lambda p: p['pair_cvs'], reverse=True)
    away_only_pairs.sort(key=lambda p: p['pair_cvs'], reverse=True)

    # Take top 4 HOME-eligible for HOME, rest go AWAY
    pairings = home_eligible[:4] + away_only_pairs + home_eligible[4:]

    # Assign HOME (1-4) and AWAY (5-8)
    print(f"\n{'=' * 70}")
    print("FINAL PAIRINGS")
    print(f"{'=' * 70}")

    rows = []
    for i, pair in enumerate(pairings, 1):
        location = "HOME" if i <= 4 else "AWAY"
        anchor = pair['anchor']
        partner = pair['gunner']

        anchor_mp = anchor['matchplay']
        partner_mp = partner['matchplay']
        anchor_mp_str = anchor_mp['record'] if anchor_mp else "New"
        partner_mp_str = partner_mp['record'] if partner_mp else "New"

        # Show pairing type
        pairing_type = pair.get('pairing_type', 'AUTO')
        wc_label = "Wildcard" if partner['is_wildcard'] else "Gunner"

        home_note = ""
        if not pair['can_play_home']:
            if not anchor['can_play_home']:
                home_note = f" [!{anchor['name']} AWAY-only]"
            if not partner['can_play_home']:
                home_note = f" [!{partner['name']} AWAY-only]"

        print(f"\nPair {i} ({location}) [{pairing_type}]{home_note}:")
        print(f"  Anchor:   {anchor['name']:<20} HI={anchor['hi']:>5.1f}  CVS={anchor['cvs']:>5.1f}  MP={anchor_mp_str}  {anchor['commitment']}  HR={anchor['home_rounds']}")
        print(f"  {wc_label:8}: {partner['name']:<20} HI={partner['hi']:>5.1f}  CVS={partner['cvs']:>5.1f}  MP={partner_mp_str}  {partner['commitment']}  HR={partner['home_rounds']}")
        print(f"  Combined CVS: {pair['pair_cvs']:.1f}  |  HI Spread: {pair['hi_spread']:.1f}")

        rows.append({
            'Pair': i,
            'Location': location,
            'Pairing Type': pairing_type,
            'Pair CVS': round(pair['pair_cvs'], 2),
            'Anchor': anchor['name'],
            'Anchor HI': anchor['hi'],
            'Anchor CVS': anchor['cvs'],
            'Anchor MP': anchor_mp_str,
            'Anchor Commitment': anchor['commitment'],
            'Anchor Home Rounds': anchor['home_rounds'],
            'Partner': partner['name'],
            'Partner Type': wc_label,
            'Partner HI': partner['hi'],
            'Partner CVS': partner['cvs'],
            'Partner MP': partner_mp_str,
            'Partner Commitment': partner['commitment'],
            'Partner Home Rounds': partner['home_rounds'],
            'HI Spread': round(pair['hi_spread'], 1)
        })

    # Save to CSV
    df = pd.DataFrame(rows)
    output_file = 'outputs/pairings_v4.csv'
    df.to_csv(output_file, index=False)

    # Summary
    home_cvs = sum(p['pair_cvs'] for p in pairings[:4])
    away_cvs = sum(p['pair_cvs'] for p in pairings[4:])
    home_committed = sum(p['committed_count'] for p in pairings[:4])
    away_committed = sum(p['committed_count'] for p in pairings[4:])

    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")

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
        wc = "WC" if p['is_wildcard'] else ""
        print(f"  {i}. {p['name']:<22} CVS={p['cvs']:>5.1f}  HI={p['hi']:>5.1f}  MP={mp_str:<12} {p['commitment']:<15} {home_status} {wc}")

    print(f"\nPairings saved to: {output_file}")

    return pairings, all_players


if __name__ == "__main__":
    generate_pairings()
