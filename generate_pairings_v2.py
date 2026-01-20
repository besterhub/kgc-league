"""
Golf League Pairings Generator v2

Creates optimal pairings for betterball match play:
- Committed players form the core
- Pairs low handicap (Anchor) with high handicap (Gunner)
- Considers matchplay win rates and recent form
- Generates 12 strongest pairs (8 play, 4 reserves)

Usage:
    python generate_pairings_v2.py
"""

import pandas as pd
import os
from itertools import combinations

def load_data():
    """Load all required data files"""
    # Load analysis data
    analysis = pd.read_csv('outputs/analysis.csv')

    # Load player list for commitment
    players_list = pd.read_csv('data/players_list.csv')
    commit_col = 'Commitmnet' if 'Commitmnet' in players_list.columns else 'Commitment'
    commitment_map = {}
    for _, row in players_list.iterrows():
        commitment_map[row['Name']] = str(row[commit_col]).strip()

    # Load matchplay records
    matchplay = pd.read_csv('outputs/matchplay_records.csv')
    matchplay_map = {}
    for _, row in matchplay.iterrows():
        matchplay_map[row['Player Name']] = {
            'wins': int(row['Wins']),
            'losses': int(row['Losses']),
            'draws': int(row['Draws']),
            'matches': int(row['Matches']),
            'win_pct': float(row['Win %'].replace('%', ''))
        }

    # Load players_info for current HI
    players_info = pd.read_csv('outputs/players_info.csv')
    hi_map = {}
    for _, row in players_info.iterrows():
        if pd.notna(row.get('Current HI')):
            hi_map[row['Player Name']] = float(row['Current HI'])

    return analysis, commitment_map, matchplay_map, hi_map


def calculate_pairing_score(player1, player2):
    """
    Calculate a pairing score based on:
    - Combined value scores
    - Matchplay win rates
    - Handicap spread (want some spread for better ball)
    """
    score = 0

    # Combined value score component (60%)
    cvs1 = player1.get('combined_score', 0) or 0
    cvs2 = player2.get('combined_score', 0) or 0
    score += (cvs1 + cvs2) * 0.6

    # Matchplay component (30%) - reward proven winners
    mp1 = player1.get('matchplay', {})
    mp2 = player2.get('matchplay', {})

    win_pct1 = mp1.get('win_pct', 40) if mp1 else 40  # Default to 40% if no history
    win_pct2 = mp2.get('win_pct', 40) if mp2 else 40

    # Bonus for experience
    matches1 = mp1.get('matches', 0) if mp1 else 0
    matches2 = mp2.get('matches', 0) if mp2 else 0
    experience_bonus = min((matches1 + matches2) / 100, 1)  # Max 1 point for 100+ combined matches

    score += ((win_pct1 + win_pct2) / 100) * 3 * 0.3  # Normalize to ~0-3 range
    score += experience_bonus * 0.5

    # Handicap spread bonus (10%) - some spread is good for betterball
    hi1 = player1.get('hi', 10)
    hi2 = player2.get('hi', 10)
    spread = abs(hi1 - hi2)

    # Ideal spread is 5-15 strokes
    if 5 <= spread <= 15:
        score += 1.0
    elif 3 <= spread <= 20:
        score += 0.5

    return score


def get_player_data(name, analysis_df, commitment_map, matchplay_map, hi_map, use_home_stats=False, home_weight=0.7):
    """Get all relevant data for a player

    Args:
        use_home_stats: If True, use HOME-only columns (HOME_Combined Value Score, etc.)
        home_weight: Weight for HOME stats when blending (0.0 = ALL only, 1.0 = HOME only, 0.7 = 70% HOME)
                     Only applies when use_home_stats is False and player has HOME data.
                     This helps reduce impact of bad away rounds (e.g., vacation golf).
    """
    player = {'name': name}

    # Get analysis data
    row = analysis_df[analysis_df['Player Name'] == name]
    if not row.empty:
        row = row.iloc[0]

        # Get both ALL and HOME scores
        all_cvs = row.get('Combined Value Score')
        home_cvs = row.get('HOME_Combined Value Score')

        if use_home_stats:
            # Pure HOME stats
            player['combined_score'] = home_cvs if pd.notna(home_cvs) else all_cvs
            player['role'] = row.get('HOME_Role', row.get('Role', 'Unknown'))
            player['performance'] = row.get('HOME_Performance Rating', row.get('Performance Rating', 'Unknown'))
            player['trend'] = row.get('HOME_Trend Rating', row.get('Trend Rating', 'Unknown'))
            player['consistency'] = row.get('HOME_Consistency Rating', row.get('Consistency Rating', 'Unknown'))
        else:
            # Blend HOME and ALL scores to reduce impact of bad away rounds
            if pd.notna(home_cvs) and pd.notna(all_cvs) and home_weight > 0:
                # Weighted blend: home_weight * HOME + (1 - home_weight) * ALL
                player['combined_score'] = (home_weight * home_cvs) + ((1 - home_weight) * all_cvs)
            else:
                player['combined_score'] = all_cvs

            player['role'] = row.get('Role', 'Unknown')
            player['performance'] = row.get('Performance Rating', 'Unknown')
            player['trend'] = row.get('Trend Rating', 'Unknown')
            player['consistency'] = row.get('Consistency Rating', 'Unknown')
    else:
        player['combined_score'] = None
        player['role'] = 'Unknown'
        player['performance'] = 'Unknown'
        player['trend'] = 'Unknown'
        player['consistency'] = 'Unknown'

    # Get commitment
    player['commitment'] = commitment_map.get(name, 'TBC')

    # Get matchplay data
    player['matchplay'] = matchplay_map.get(name)

    # Get handicap
    player['hi'] = hi_map.get(name, 15)  # Default to 15 if unknown

    return player


def generate_pairings(use_home_stats=False, home_weight=0.7):
    """Generate optimal pairings

    Args:
        use_home_stats: If True, use HOME-only stats for scoring (default: False)
        home_weight: Weight for HOME stats when blending (0.0 = ALL only, 1.0 = HOME only)
                     Default 0.7 means 70% HOME + 30% ALL to reduce impact of bad away rounds.
    """
    print("="*60)
    print("GOLF LEAGUE PAIRINGS GENERATOR v2")
    if use_home_stats:
        print("*** USING HOME-ONLY STATS ***")
    else:
        print(f"*** BLENDED STATS: {int(home_weight*100)}% HOME + {int((1-home_weight)*100)}% ALL ***")
    print("="*60)

    # Load data
    analysis, commitment_map, matchplay_map, hi_map = load_data()

    # Get all players with their data
    all_players = []

    # First, get committed players (Full commitment)
    committed_names = [name for name, commit in commitment_map.items() if commit == 'Full']
    print(f"\nCommitted players (Full): {len(committed_names)}")

    for name in committed_names:
        player = get_player_data(name, analysis, commitment_map, matchplay_map, hi_map,
                                  use_home_stats=use_home_stats, home_weight=home_weight)
        all_players.append(player)
        mp = player['matchplay']
        mp_str = f"{mp['wins']}-{mp['losses']}-{mp['draws']} ({mp['win_pct']:.1f}%)" if mp else "No history"
        cvs_str = f"{player.get('combined_score'):.1f}" if player.get('combined_score') is not None else "N/A"
        print(f"  {name}: HI={player['hi']:.1f}, CVS={cvs_str}, Role={player['role']}, MP={mp_str}")

    # Add ad-hoc players if we need more
    adhoc_names = [name for name, commit in commitment_map.items() if commit == 'Month-2-month']
    print(f"\nAd-hoc players (Month-2-month): {len(adhoc_names)}")

    for name in adhoc_names:
        player = get_player_data(name, analysis, commitment_map, matchplay_map, hi_map,
                                  use_home_stats=use_home_stats, home_weight=home_weight)
        all_players.append(player)

    # Add TBC players as third tier to ensure we have enough for 12 pairs
    tbc_names = [name for name, commit in commitment_map.items() if commit.strip() == 'TBC']
    print(f"\nTBC players: {len(tbc_names)}")

    for name in tbc_names:
        player = get_player_data(name, analysis, commitment_map, matchplay_map, hi_map,
                                  use_home_stats=use_home_stats, home_weight=home_weight)
        all_players.append(player)

    # Filter to players with sufficient data
    valid_players = [p for p in all_players if p.get('combined_score') is not None or p.get('matchplay') is not None]
    print(f"\nValid players for pairing: {len(valid_players)}")

    # Sort by a composite score (CVS + matchplay bonus)
    def player_strength(p):
        cvs = p.get('combined_score') or 0
        mp = p.get('matchplay')
        mp_bonus = (mp['win_pct'] / 100 * 2) if mp and mp['matches'] >= 5 else 0
        return cvs + mp_bonus

    # PRIORITY: All committed (Full) players first, then fill with others by strength
    committed_valid = [p for p in valid_players if p['commitment'] == 'Full']
    adhoc_valid = [p for p in valid_players if p['commitment'] == 'Month-2-month']
    tbc_valid = [p for p in valid_players if p['commitment'].strip() == 'TBC']

    # Sort each group by strength
    committed_valid.sort(key=player_strength, reverse=True)
    adhoc_valid.sort(key=player_strength, reverse=True)
    tbc_valid.sort(key=player_strength, reverse=True)

    print(f"\nCommitted (Full) with data: {len(committed_valid)}")
    print(f"Ad-hoc (Month-2-month) with data: {len(adhoc_valid)}")
    print(f"TBC with data: {len(tbc_valid)}")

    # Build top 24: all committed first, then fill with ad-hoc, then TBC
    top_players = []
    top_players.extend(committed_valid)  # All committed players included

    # Fill remaining slots with ad-hoc players (by strength)
    remaining_slots = 24 - len(top_players)
    if remaining_slots > 0:
        top_players.extend(adhoc_valid[:remaining_slots])

    # If still need more, add TBC players
    remaining_slots = 24 - len(top_players)
    if remaining_slots > 0:
        top_players.extend(tbc_valid[:remaining_slots])

    print(f"\nTop 24 players for pairing:")
    for i, p in enumerate(top_players, 1):
        mp = p['matchplay']
        mp_str = f"{mp['wins']}-{mp['losses']}-{mp['draws']}" if mp else "No MP"
        cvs = f"{p['combined_score']:.1f}" if p.get('combined_score') else "N/A"
        print(f"  {i:2}. {p['name']:25} HI={p['hi']:5.1f}  CVS={cvs:>5}  {mp_str:12}  {p['role']:10}  {p['commitment']}")

    # Split into low and high handicappers for Anchor/Gunner pairing
    median_hi = sorted([p['hi'] for p in top_players])[len(top_players)//2]
    print(f"\nMedian handicap: {median_hi:.1f}")

    low_hi = [p for p in top_players if p['hi'] < median_hi]
    high_hi = [p for p in top_players if p['hi'] >= median_hi]

    print(f"Low handicappers (<{median_hi:.1f}): {len(low_hi)}")
    print(f"High handicappers (>={median_hi:.1f}): {len(high_hi)}")

    # Generate all possible pairings and score them
    print("\n" + "="*60)
    print("GENERATING OPTIMAL PAIRINGS")
    print("="*60)

    # ============================================================
    # REQUIRED PAIRINGS (constraints)
    # ============================================================
    required_pairings = [
        ('Greg Park', 'Hugo Lamprecht'),  # Must be together
    ]

    # Matt Maritz must be with either Grant Syme OR Ian Scott
    matt_options = [
        ('Matt Maritz', 'Grant Syme'),
        ('Matt Maritz', 'Ian Scott'),
    ]

    best_pairings = []
    used_players = set()

    # Helper to find player by name
    def find_player(name):
        for p in top_players:
            if p['name'] == name:
                return p
        return None

    # First, add required pairings
    print("\nApplying required pairings...")
    for name1, name2 in required_pairings:
        p1 = find_player(name1)
        p2 = find_player(name2)
        if p1 and p2:
            score = calculate_pairing_score(p1, p2)
            best_pairings.append(((p1, p2), score))
            used_players.add(name1)
            used_players.add(name2)
            print(f"  REQUIRED: {name1} + {name2} (Score: {score:.2f})")
        else:
            missing = name1 if not p1 else name2
            print(f"  WARNING: Could not find {missing} for required pairing")

    # Handle Matt Maritz constraint - pick best available option
    print("\nApplying Matt Maritz constraint (must pair with Grant Syme OR Ian Scott)...")
    best_matt_pair = None
    best_matt_score = -1
    for name1, name2 in matt_options:
        p1 = find_player(name1)
        p2 = find_player(name2)
        if p1 and p2 and name1 not in used_players and name2 not in used_players:
            score = calculate_pairing_score(p1, p2)
            if score > best_matt_score:
                best_matt_score = score
                best_matt_pair = (p1, p2, name1, name2)

    if best_matt_pair:
        p1, p2, name1, name2 = best_matt_pair
        best_pairings.append(((p1, p2), best_matt_score))
        used_players.add(name1)
        used_players.add(name2)
        print(f"  CONSTRAINT: {name1} + {name2} (Score: {best_matt_score:.2f})")
    else:
        print(f"  WARNING: Could not satisfy Matt Maritz constraint")

    # ============================================================
    # Fill remaining pairs with BALANCED approach
    # Goal: Minimize variance between pair scores (spread strength evenly)
    # ============================================================
    print("\nFilling remaining pairs (balanced optimization)...")
    remaining_pairs = 12 - len(best_pairings)

    # Get all available players
    available_players = [p for p in top_players if p['name'] not in used_players]

    # Generate all possible pairs and their scores
    all_possible_pairs = []
    for p1, p2 in combinations(available_players, 2):
        score = calculate_pairing_score(p1, p2)
        all_possible_pairs.append((p1, p2, score))

    # Sort by score
    all_possible_pairs.sort(key=lambda x: x[2], reverse=True)

    # Strategy: Alternate between picking from top and bottom to balance
    # First, use a balanced selection approach
    def find_balanced_pairings(pairs_needed, available_pairs):
        """Find pairings that balance scores across all pairs"""
        from itertools import combinations as iter_combinations

        best_solution = None
        best_variance = float('inf')
        best_min_score = -1

        # Try multiple random samples to find good balanced solution
        import random

        # For small sets, try to be more exhaustive
        # For larger sets, use sampling
        available_pairs_list = list(available_pairs)

        # Greedy balanced approach: alternate high/low picks
        def greedy_balanced():
            selected = []
            used = set()
            remaining = list(available_pairs_list)

            while len(selected) < pairs_needed and remaining:
                # Filter to valid pairs (no used players)
                valid = [(p1, p2, s) for p1, p2, s in remaining
                        if p1['name'] not in used and p2['name'] not in used]

                if not valid:
                    break

                # If we have few pairs, pick middle-ish score
                # If we have many, alternate between higher and lower
                if len(selected) % 2 == 0:
                    # Pick from top third
                    idx = min(len(valid) // 4, len(valid) - 1)
                else:
                    # Pick from middle
                    idx = len(valid) // 2

                p1, p2, score = valid[idx]
                selected.append((p1, p2, score))
                used.add(p1['name'])
                used.add(p2['name'])
                remaining = [(a, b, s) for a, b, s in remaining
                            if a['name'] not in used and b['name'] not in used]

            return selected

        # Try greedy balanced
        solution = greedy_balanced()

        # Also try pure greedy for comparison
        def pure_greedy():
            selected = []
            used = set()
            for p1, p2, score in available_pairs_list:
                if p1['name'] not in used and p2['name'] not in used:
                    selected.append((p1, p2, score))
                    used.add(p1['name'])
                    used.add(p2['name'])
                    if len(selected) >= pairs_needed:
                        break
            return selected

        greedy_solution = pure_greedy()

        # Compare variance and minimum scores
        def evaluate(sol):
            if len(sol) < pairs_needed:
                return float('inf'), -1
            scores = [s for _, _, s in sol]
            avg = sum(scores) / len(scores)
            variance = sum((s - avg) ** 2 for s in scores) / len(scores)
            min_score = min(scores)
            return variance, min_score

        bal_var, bal_min = evaluate(solution)
        greedy_var, greedy_min = evaluate(greedy_solution)

        # Prefer solution with higher minimum score (stronger weakest pair)
        # If mins are similar, prefer lower variance
        if bal_min > greedy_min + 0.5:
            return solution
        elif greedy_min > bal_min + 0.5:
            return greedy_solution
        elif bal_var < greedy_var:
            return solution
        else:
            return greedy_solution

    balanced_pairs = find_balanced_pairings(remaining_pairs, all_possible_pairs)

    for p1, p2, score in balanced_pairs:
        best_pairings.append(((p1, p2), score))
        used_players.add(p1['name'])
        used_players.add(p2['name'])

    # Display pairings
    print("\n" + "="*60)
    print("RECOMMENDED PAIRINGS (Sorted by Pair Strength)")
    print("="*60)

    # Sort by score
    best_pairings.sort(key=lambda x: x[1], reverse=True)

    rows = []
    for i, (pair, score) in enumerate(best_pairings, 1):
        p1, p2 = pair

        # Determine which is anchor (lower HI)
        if p1['hi'] <= p2['hi']:
            anchor, gunner = p1, p2
        else:
            anchor, gunner = p2, p1

        mp_a = anchor['matchplay']
        mp_g = gunner['matchplay']

        mp_a_str = f"{mp_a['wins']}-{mp_a['losses']}-{mp_a['draws']}" if mp_a else "New"
        mp_g_str = f"{mp_g['wins']}-{mp_g['losses']}-{mp_g['draws']}" if mp_g else "New"

        status = "PLAY" if i <= 8 else "RESERVE"

        cvs_a = f"{anchor.get('combined_score', 0):.1f}" if anchor.get('combined_score') else "N/A"
        cvs_g = f"{gunner.get('combined_score', 0):.1f}" if gunner.get('combined_score') else "N/A"

        print(f"\n{status} Pair {i:2} (Score: {score:.2f})")
        print(f"  Anchor: {anchor['name']:25} HI={anchor['hi']:5.1f}  CVS={cvs_a:>5}  MP={mp_a_str}")
        print(f"  Gunner: {gunner['name']:25} HI={gunner['hi']:5.1f}  CVS={cvs_g:>5}  MP={mp_g_str}")

        rows.append({
            'Pair': i,
            'Status': status,
            'Pair Score': round(score, 2),
            'Anchor': anchor['name'],
            'Anchor HI': anchor['hi'],
            'Anchor CVS': anchor.get('combined_score'),
            'Anchor MP': mp_a_str,
            'Anchor Commitment': anchor['commitment'],
            'Gunner': gunner['name'],
            'Gunner HI': gunner['hi'],
            'Gunner CVS': gunner.get('combined_score'),
            'Gunner MP': mp_g_str,
            'Gunner Commitment': gunner['commitment'],
            'HI Spread': abs(anchor['hi'] - gunner['hi'])
        })

    # Save to CSV
    df = pd.DataFrame(rows)
    output_file = 'outputs/pairings_v2.csv'
    df.to_csv(output_file, index=False)

    print("\n" + "="*60)
    print(f"PAIRINGS SAVED TO {output_file}")
    print("="*60)

    # Summary stats
    play_pairs = [r for r in rows if r['Status'] == 'PLAY']
    reserve_pairs = [r for r in rows if r['Status'] == 'RESERVE']

    print(f"\nPlaying pairs: {len(play_pairs)}")
    print(f"Reserve pairs: {len(reserve_pairs)}")

    committed_count = sum(1 for r in rows for name in [r['Anchor'], r['Gunner']]
                         if commitment_map.get(name) == 'Full')
    print(f"Committed players in pairings: {committed_count}")

    # Score balance summary
    all_scores = [r['Pair Score'] for r in rows]
    play_scores = [r['Pair Score'] for r in play_pairs]
    reserve_scores = [r['Pair Score'] for r in reserve_pairs]

    print(f"\n" + "-"*40)
    print("SCORE BALANCE SUMMARY")
    print("-"*40)
    print(f"All pairs:     avg={sum(all_scores)/len(all_scores):.2f}, min={min(all_scores):.2f}, max={max(all_scores):.2f}, range={max(all_scores)-min(all_scores):.2f}")
    print(f"Playing (1-8): avg={sum(play_scores)/len(play_scores):.2f}, min={min(play_scores):.2f}, max={max(play_scores):.2f}, range={max(play_scores)-min(play_scores):.2f}")
    if reserve_scores:
        print(f"Reserve (9-12): avg={sum(reserve_scores)/len(reserve_scores):.2f}, min={min(reserve_scores):.2f}, max={max(reserve_scores):.2f}, range={max(reserve_scores)-min(reserve_scores):.2f}")


if __name__ == "__main__":
    generate_pairings()
