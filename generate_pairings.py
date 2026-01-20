"""
Golf League Pairing Strategy

Pairing Strategy:
1. Select top 8 Anchor players by Combined Value Score
2. Select top 8 Gunner players by Combined Value Score
3. Wildcard players can fill either role as needed
4. Use optimization to pair anchors with gunners while:
   - Respecting required pairings and exclusions
   - Ensuring minimum handicap difference between paired players
   - Maximizing total combined score

Usage:
    python generate_pairings.py
"""

import pandas as pd
import os
from itertools import permutations


def load_course_handicaps(scores_file):
    """Load latest course handicaps for Krugersdorp from scores data"""
    scores = pd.read_csv(scores_file)

    # Filter to Krugersdorp only (full 18-hole rounds)
    kgc_scores = scores[
        (scores['Club Played'] == 'KRUGERSDORP GOLF CLUB') &
        (scores['Tee'] == 72)
    ].copy()

    # Parse dates
    kgc_scores['Date'] = pd.to_datetime(
        kgc_scores['Date Played'].str.replace(' am| pm', '', regex=True),
        format='%d-%m-%Y'
    )

    # Get latest CH for each player at Krugersdorp
    latest_ch = kgc_scores.sort_values('Date', ascending=False).groupby('Player Name').first()[['CH']].reset_index()

    return dict(zip(latest_ch['Player Name'], latest_ch['CH']))


def generate_pairings(input_file, output_file=None, min_rounds=10, scores_file=None):
    """Generate team pairings based on player type and combined score"""

    print("=" * 60)
    print("GOLF LEAGUE PAIRING GENERATOR")
    print("=" * 60)

    # Read analysis data
    df = pd.read_csv(input_file)

    # Load course handicaps if scores file provided
    if scores_file and os.path.exists(scores_file):
        ch_lookup = load_course_handicaps(scores_file)
    else:
        ch_lookup = {}

    # Filter to players with valid Combined Value Score and minimum rounds
    df_valid = df[
        (df['Combined Value Score'].notna()) &
        (df['Total Rounds (12 weeks)'] >= min_rounds)
    ].copy()

    print(f"\nPlayers with valid scores and >= {min_rounds} rounds: {len(df_valid)}")

    # Split by Role (Anchor, Wildcard, Gunner)
    anchor_players = df_valid[df_valid['Role'] == 'Anchor'].sort_values(
        'Combined Value Score', ascending=False
    )
    wildcard_players = df_valid[df_valid['Role'] == 'Wildcard'].sort_values(
        'Combined Value Score', ascending=False
    )
    gunner_players = df_valid[df_valid['Role'] == 'Gunner'].sort_values(
        'Combined Value Score', ascending=False
    )

    print(f"Anchor players available: {len(anchor_players)}")
    print(f"Wildcard players available: {len(wildcard_players)}")
    print(f"Gunner players available: {len(gunner_players)}")

    # Select players for anchor role (Anchors first, then Wildcard to fill)
    top_anchors = anchor_players.copy()
    if len(top_anchors) < 8:
        needed = 8 - len(top_anchors)
        top_anchors = pd.concat([top_anchors, wildcard_players.head(needed)])
    top_anchors = top_anchors.head(8).reset_index(drop=True)

    # Select players for gunner role (Gunners first, then remaining Wildcard)
    used_wildcard = top_anchors[top_anchors['Role'] == 'Wildcard']['Player Name'].tolist()
    remaining_wildcard = wildcard_players[~wildcard_players['Player Name'].isin(used_wildcard)]

    top_gunners = gunner_players.copy()
    if len(top_gunners) < 8:
        needed = 8 - len(top_gunners)
        top_gunners = pd.concat([top_gunners, remaining_wildcard.head(needed)])
    top_gunners = top_gunners.head(8).reset_index(drop=True)

    print(f"\nSelected {len(top_anchors)} players for Anchor role")
    print(f"Selected {len(top_gunners)} players for Gunner role")

    # Display selected players with CH
    print("\n" + "-" * 60)
    print("SELECTED ANCHORS (Top 8 by Combined Score)")
    print("-" * 60)
    for i, row in top_anchors.iterrows():
        ch = int(ch_lookup.get(row['Player Name'], 0))
        print(f"  {i+1}. {row['Player Name']:<25} Score: {row['Combined Value Score']:.1f}  "
              f"CH: {ch:<3} Role: {row['Role']:<8} Cons: {row['Consistency Rating']}")

    print("\n" + "-" * 60)
    print("SELECTED GUNNERS (Top 8 by Combined Score)")
    print("-" * 60)
    for i, row in top_gunners.iterrows():
        ch = int(ch_lookup.get(row['Player Name'], 0))
        print(f"  {i+1}. {row['Player Name']:<25} Score: {row['Combined Value Score']:.1f}  "
              f"CH: {ch:<3} Role: {row['Role']:<8} Cons: {row['Consistency Rating']}")

    # ===== PAIRING CONSTRAINTS =====
    # Define required pairings and exclusions
    REQUIRED_PAIRINGS = [
        ('Greg Park', 'Hugo Lamprecht'),  # Greg must play with Hugo
    ]

    # Either Ian or Grant must play with Matt
    EITHER_OR_PAIRINGS = [
        (['Ian Scott', 'Grant Syme'], 'Matt Maritz'),
    ]

    # Jacques cannot play with these players
    EXCLUSIONS = {
        'Jacques vd Berg': ['Gerdus Theron', 'Frank Coetzee', 'Marcelle Smith'],
    }

    # Minimum course handicap difference for pairing balance
    MIN_CH_DIFF = 2

    # Ensure required players are in the pools
    # Add any missing required players to appropriate pools
    all_required_players = set()
    for anchor, gunner in REQUIRED_PAIRINGS:
        all_required_players.add(anchor)
        all_required_players.add(gunner)
    for anchor_options, gunner in EITHER_OR_PAIRINGS:
        all_required_players.update(anchor_options)
        all_required_players.add(gunner)

    added_players = []
    for player_name in all_required_players:
        player = df_valid[df_valid['Player Name'] == player_name]
        if len(player) > 0:
            player_row = player.iloc[0]
            in_anchors = player_name in top_anchors['Player Name'].values
            in_gunners = player_name in top_gunners['Player Name'].values
            if not in_anchors and not in_gunners:
                # Add to appropriate pool based on role
                if player_row['Role'] in ['Anchor', 'Wildcard']:
                    top_anchors = pd.concat([top_anchors, player.reset_index(drop=True)], ignore_index=True)
                    added_players.append(f"{player_name} -> anchors")
                else:
                    top_gunners = pd.concat([top_gunners, player.reset_index(drop=True)], ignore_index=True)
                    added_players.append(f"{player_name} -> gunners")

    if added_players:
        print(f"\nAdded required players to pools: {', '.join(added_players)}")

    print("\n" + "-" * 60)
    print("PAIRING CONSTRAINTS")
    print("-" * 60)
    print("  Required: Greg Park + Hugo Lamprecht")
    print("  Required: Either Ian Scott OR Grant Syme + Matt Maritz")
    print("  Excluded: Jacques vd Berg cannot pair with Gerdus, Frank, or Marcelle")
    print(f"  Minimum CH difference: {MIN_CH_DIFF} strokes")

    # Create score lookup
    score_lookup = dict(zip(df_valid['Player Name'], df_valid['Combined Value Score']))

    # Helper function to find player row by name
    def find_player(df, name):
        matches = df[df['Player Name'] == name]
        return matches.iloc[0] if len(matches) > 0 else None

    def get_ch_diff(anchor_name, gunner_name):
        anchor_ch = ch_lookup.get(anchor_name, 0)
        gunner_ch = ch_lookup.get(gunner_name, 0)
        return abs(gunner_ch - anchor_ch)

    def is_valid_pairing(anchor_name, gunner_name):
        """Check if pairing meets all constraints"""
        # Check exclusions
        if gunner_name in EXCLUSIONS.get(anchor_name, []):
            return False
        # Check CH difference (only if we have CH data)
        if ch_lookup:
            ch_diff = get_ch_diff(anchor_name, gunner_name)
            if ch_diff < MIN_CH_DIFF:
                return False
        return True

    def get_combined_score(anchor_name, gunner_name):
        return score_lookup.get(anchor_name, 0) + score_lookup.get(gunner_name, 0)

    # Start with required pairings
    fixed_pairs = []
    used_anchors = set()
    used_gunners = set()

    # 1. Handle required pairings first
    for anchor_name, gunner_name in REQUIRED_PAIRINGS:
        # Find both players in either pool
        anchor = find_player(top_anchors, anchor_name)
        if anchor is None:
            anchor = find_player(top_gunners, anchor_name)

        gunner = find_player(top_gunners, gunner_name)
        if gunner is None:
            gunner = find_player(top_anchors, gunner_name)

        if anchor is not None and gunner is not None:
            used_anchors.add(anchor['Player Name'])
            used_gunners.add(gunner['Player Name'])
            fixed_pairs.append((anchor['Player Name'], gunner['Player Name'], "REQUIRED"))

    # 2. Handle either/or pairings
    for anchor_options, gunner_name in EITHER_OR_PAIRINGS:
        gunner = find_player(top_gunners, gunner_name)
        if gunner is None:
            gunner = find_player(top_anchors, gunner_name)

        if gunner is not None and gunner['Player Name'] not in used_gunners:
            # Try each anchor option in order of preference
            for anchor_name in anchor_options:
                anchor = find_player(top_anchors, anchor_name)
                if anchor is None:
                    anchor = find_player(top_gunners, anchor_name)

                if anchor is not None and anchor['Player Name'] not in used_anchors:
                    used_anchors.add(anchor['Player Name'])
                    used_gunners.add(gunner['Player Name'])
                    fixed_pairs.append((anchor['Player Name'], gunner['Player Name'], "REQUIRED (either/or)"))
                    break

    # 3. Optimize remaining pairs
    # Combine used players from both anchor and gunner positions
    all_used_players = used_anchors | used_gunners

    remaining_anchors = [row['Player Name'] for _, row in top_anchors.iterrows()
                         if row['Player Name'] not in all_used_players]
    remaining_gunners = [row['Player Name'] for _, row in top_gunners.iterrows()
                         if row['Player Name'] not in all_used_players]

    # Find optimal assignment using permutation search
    best_assignment = None
    best_total_score = -1

    for perm in permutations(remaining_gunners):
        valid = True
        total_score = 0

        for anchor, gunner in zip(remaining_anchors, perm):
            if not is_valid_pairing(anchor, gunner):
                valid = False
                break
            total_score += get_combined_score(anchor, gunner)

        if valid and total_score > best_total_score:
            best_total_score = total_score
            best_assignment = list(zip(remaining_anchors, perm))

    if best_assignment is None:
        print("\nWARNING: Could not find valid assignment meeting all constraints!")
        print("Falling back to greedy assignment (may violate CH constraint)")
        # Fallback to greedy assignment
        best_assignment = []
        temp_used_gunners = set()
        for anchor in remaining_anchors:
            for gunner in remaining_gunners:
                if gunner not in temp_used_gunners and gunner not in EXCLUSIONS.get(anchor, []):
                    best_assignment.append((anchor, gunner))
                    temp_used_gunners.add(gunner)
                    break

    # Combine all pairs
    all_pairs = []

    # Add fixed pairs
    for anchor_name, gunner_name, constraint in fixed_pairs:
        anchor = find_player(top_anchors, anchor_name)
        if anchor is None:
            anchor = find_player(top_gunners, anchor_name)
        gunner = find_player(top_gunners, gunner_name)
        if gunner is None:
            gunner = find_player(top_anchors, gunner_name)
        ch_diff = get_ch_diff(anchor_name, gunner_name)
        all_pairs.append((anchor, gunner, constraint, ch_diff))

    # Add optimized pairs
    for anchor_name, gunner_name in best_assignment:
        anchor = find_player(top_anchors, anchor_name)
        gunner = find_player(top_gunners, gunner_name)
        ch_diff = get_ch_diff(anchor_name, gunner_name)
        all_pairs.append((anchor, gunner, "AUTO", ch_diff))

    # Sort pairings by combined score for display
    all_pairs = sorted(all_pairs, key=lambda x: x[0]['Combined Value Score'] + x[1]['Combined Value Score'], reverse=True)

    print("\n" + "=" * 60)
    print("RECOMMENDED PAIRINGS")
    print("(Optimized for constraints + handicap balance)")
    print("=" * 60)

    pairing_records = []
    for i, (anchor, gunner, constraint_type, ch_diff) in enumerate(all_pairs):
        pair_combined = anchor['Combined Value Score'] + gunner['Combined Value Score']
        anchor_ch = int(ch_lookup.get(anchor['Player Name'], 0))
        gunner_ch = int(ch_lookup.get(gunner['Player Name'], 0))

        pairing = {
            'Pair': i + 1,
            'Anchor': anchor['Player Name'],
            'Anchor Score': anchor['Combined Value Score'],
            'Anchor CH': anchor_ch,
            'Anchor Perf': anchor['Performance Rating'],
            'Anchor Location': anchor['Preferred Location'],
            'Gunner': gunner['Player Name'],
            'Gunner Score': gunner['Combined Value Score'],
            'Gunner CH': gunner_ch,
            'Gunner Perf': gunner['Performance Rating'],
            'Gunner Location': gunner['Preferred Location'],
            'CH Diff': int(ch_diff),
            'Pair Combined Score': pair_combined,
            'Constraint': constraint_type,
        }
        pairing_records.append(pairing)

        constraint_label = f" [{constraint_type}]" if constraint_type != "AUTO" else ""
        print(f"\nPair {i+1}:{constraint_label}")
        print(f"  Anchor: {anchor['Player Name']:<20} (Score: {anchor['Combined Value Score']:.1f}, "
              f"CH: {anchor_ch}, {anchor['Performance Rating']}, {anchor['Preferred Location']})")
        print(f"  Gunner: {gunner['Player Name']:<20} (Score: {gunner['Combined Value Score']:.1f}, "
              f"CH: {gunner_ch}, {gunner['Performance Rating']}, {gunner['Preferred Location']})")
        print(f"  Pair Combined Score: {pair_combined:.1f}  |  CH Diff: {int(ch_diff)}")

    # Create pairings DataFrame
    pairings_df = pd.DataFrame(pairing_records)

    # Calculate pair score statistics
    avg_pair_score = pairings_df['Pair Combined Score'].mean()
    min_pair_score = pairings_df['Pair Combined Score'].min()
    max_pair_score = pairings_df['Pair Combined Score'].max()
    avg_ch_diff = pairings_df['CH Diff'].mean()
    min_ch_diff = pairings_df['CH Diff'].min()

    print("\n" + "-" * 60)
    print("PAIR BALANCE ANALYSIS")
    print("-" * 60)
    print(f"  Average Pair Score: {avg_pair_score:.1f}")
    print(f"  Min Pair Score: {min_pair_score:.1f}")
    print(f"  Max Pair Score: {max_pair_score:.1f}")
    print(f"  Score Range: {max_pair_score - min_pair_score:.1f}")
    print(f"  Average CH Diff: {avg_ch_diff:.1f}")
    print(f"  Min CH Diff: {min_ch_diff}")

    # Location recommendation
    print("\n" + "-" * 60)
    print("LOCATION RECOMMENDATIONS")
    print("-" * 60)

    home_preferred = []
    away_preferred = []
    any_location = []

    for _, pair in pairings_df.iterrows():
        anchor_loc = pair['Anchor Location']
        gunner_loc = pair['Gunner Location']

        # Determine pair preference based on both players
        home_signals = sum(1 for loc in [anchor_loc, gunner_loc] if 'HOME' in str(loc))
        away_signals = sum(1 for loc in [anchor_loc, gunner_loc] if 'AWAY' in str(loc))

        pair_info = f"Pair {pair['Pair']}: {pair['Anchor']} + {pair['Gunner']}"

        if home_signals > away_signals:
            home_preferred.append(pair_info)
        elif away_signals > home_signals:
            away_preferred.append(pair_info)
        else:
            any_location.append(pair_info)

    print("\nHOME preference:")
    for p in home_preferred:
        print(f"  {p}")

    print("\nAWAY preference:")
    for p in away_preferred:
        print(f"  {p}")

    print("\nFlexible (ANY):")
    for p in any_location:
        print(f"  {p}")

    # Save to CSV if output file specified
    if output_file:
        pairings_df.to_csv(output_file, index=False)
        print(f"\n{'=' * 60}")
        print(f"Pairings saved to: {output_file}")

    # Show reserves
    print("\n" + "=" * 60)
    print("RESERVES")
    print("=" * 60)

    # Get all players used in pairings
    used_players = set(top_anchors['Player Name'].tolist() + top_gunners['Player Name'].tolist())

    # Find remaining players not used
    reserve_players = df_valid[~df_valid['Player Name'].isin(used_players)].sort_values(
        'Combined Value Score', ascending=False
    )

    if len(reserve_players) > 0:
        print("\nReserve players (by Role):")
        for role in ['Anchor', 'Wildcard', 'Gunner']:
            role_reserves = reserve_players[reserve_players['Role'] == role]
            if len(role_reserves) > 0:
                print(f"\n  {role}s:")
                for _, row in role_reserves.iterrows():
                    ch = int(ch_lookup.get(row['Player Name'], 0))
                    print(f"    {row['Player Name']:<25} Score: {row['Combined Value Score']:.1f}  CH: {ch}")

    return pairings_df


def main():
    """Main execution function"""

    input_file = "outputs/analysis.csv"
    output_file = "outputs/pairings.csv"
    scores_file = "outputs/scores.csv"

    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        return

    generate_pairings(input_file, output_file, scores_file=scores_file)


if __name__ == "__main__":
    main()
