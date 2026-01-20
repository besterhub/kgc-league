"""
Golf Score Analysis Script

Analyzes player performance from scores.csv and generates:
- Total rounds in the last 12 weeks
- Average rounds per week
- Average difference between DIFF and OPEN HI (for HOME, AWAY, and ALL)
- Consistency metric (standard deviation of DIFF - OPEN HI)
- Trend analysis for DIFF - OPEN HI (recent 6 weeks vs oldest 6 weeks)
- Player type classification (Steady vs Explosive) for team pairing strategy

Uses BLENDED scoring: 70% HOME stats + 30% ALL stats
This reduces the impact of bad away rounds (e.g., vacation golf) while still
accounting for overall performance.

Usage:
    python analyze_scores.py
"""

import pandas as pd
from datetime import datetime, timedelta
import os

def clean_diff_value(diff_str):
    """Remove 'c' and 'e' suffixes from DIFF values and convert to float"""
    if pd.isna(diff_str) or diff_str == '':
        return None
    # Remove 'c', 'e' and any whitespace, then convert to float
    cleaned = str(diff_str).replace('c', '').replace('e', '').strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def analyze_player_data(player_name, player_data, six_weeks_ago, CONSISTENCY_FACTOR=0.10):
    """
    Analyze a single player's data and return metrics dictionary.
    This function is called twice per player - once for ALL rounds, once for HOME-only.
    """
    # Total rounds in last 12 weeks
    total_rounds = len(player_data)

    if total_rounds == 0:
        return None

    # Average rounds per week
    avg_rounds_per_week = total_rounds / 12

    # Split data by location
    home_data = player_data[player_data['Location'] == 'HOME']
    away_data = player_data[player_data['Location'] == 'AWAY']

    # Calculate home game percentage
    home_rounds = len(home_data)
    home_percentage = (home_rounds / total_rounds * 100) if total_rounds > 0 else 0

    # Calculate average DIFF - OPEN HI for ALL, HOME, AWAY (12 weeks)
    all_diff_12w = player_data['DIFF_minus_OPEN_HI'].mean()
    all_std = player_data['DIFF_minus_OPEN_HI'].std()

    home_diff = home_data['DIFF_minus_OPEN_HI'].mean() if len(home_data) > 0 else None
    home_std = home_data['DIFF_minus_OPEN_HI'].std() if len(home_data) > 0 else None

    away_diff = away_data['DIFF_minus_OPEN_HI'].mean() if len(away_data) > 0 else None
    away_std = away_data['DIFF_minus_OPEN_HI'].std() if len(away_data) > 0 else None

    # Calculate trend metrics: recent 6 weeks vs oldest 6 weeks
    player_data_recent_6w = player_data[player_data['Date Played'] >= six_weeks_ago]
    player_data_oldest_6w = player_data[player_data['Date Played'] < six_weeks_ago]

    rounds_recent_6w = len(player_data_recent_6w)
    rounds_oldest_6w = len(player_data_oldest_6w)

    all_diff_recent_6w = player_data_recent_6w['DIFF_minus_OPEN_HI'].mean() if rounds_recent_6w > 0 else None
    all_diff_oldest_6w = player_data_oldest_6w['DIFF_minus_OPEN_HI'].mean() if rounds_oldest_6w > 0 else None

    # Calculate confidence weight based on rounds played in each period
    if rounds_recent_6w > 0 and rounds_oldest_6w > 0:
        trend_confidence = min(rounds_recent_6w, rounds_oldest_6w) / max(rounds_recent_6w, rounds_oldest_6w)
    else:
        trend_confidence = 0

    # Calculate player type metrics
    volatility_index = all_std if pd.notna(all_std) else 0

    # Coefficient of Variation (CV) = StdDev / Mean
    if pd.notna(all_std) and pd.notna(all_diff_12w) and all_diff_12w != 0:
        coefficient_of_variation = abs(all_std / all_diff_12w)
    else:
        coefficient_of_variation = None

    # Classify player type based on consistency
    if pd.notna(all_std):
        player_type = "Steady" if all_std < 2.5 else "Explosive"
    else:
        player_type = "Unknown"

    # Weighted trend change
    if pd.notna(all_diff_recent_6w) and pd.notna(all_diff_oldest_6w) and trend_confidence > 0:
        raw_trend_change = all_diff_recent_6w - all_diff_oldest_6w
        weighted_trend_change = raw_trend_change * trend_confidence
    else:
        weighted_trend_change = None

    # Get player's average handicap index over the period
    avg_handicap = player_data['OPEN HI_clean'].mean()

    # Calculate adjusted StdDev
    if pd.notna(all_std) and pd.notna(avg_handicap):
        adjusted_std = all_std + (avg_handicap * CONSISTENCY_FACTOR)
    else:
        adjusted_std = None

    # Calculate preferred location (only meaningful for ALL rounds data)
    preferred_location = "ANY"
    location_advantage = None

    if pd.notna(home_diff) and pd.notna(away_diff) and len(home_data) >= 3 and len(away_data) >= 3:
        location_advantage = away_diff - home_diff

        if location_advantage > 1.0:
            preferred_location = "HOME (Strong)"
        elif location_advantage > 0.5:
            preferred_location = "HOME"
        elif location_advantage < -1.0:
            preferred_location = "AWAY (Strong)"
        elif location_advantage < -0.5:
            preferred_location = "AWAY"
        else:
            preferred_location = "ANY"
    elif len(home_data) < 3 and len(away_data) >= 3:
        preferred_location = "AWAY (Limited Home Data)"
    elif len(away_data) < 3 and len(home_data) >= 3:
        preferred_location = "HOME (Limited Away Data)"
    else:
        preferred_location = "ANY (Insufficient Data)"

    return {
        'Player Name': player_name,
        'Total Rounds (12 weeks)': total_rounds,
        'Avg Rounds per Week': round(avg_rounds_per_week, 2),
        'Home Games %': round(home_percentage, 1),
        'Avg DIFF - OPEN HI (ALL)': round(all_diff_12w, 2) if pd.notna(all_diff_12w) else None,
        'Avg DIFF - OPEN HI (HOME)': round(home_diff, 2) if pd.notna(home_diff) else None,
        'Avg DIFF - OPEN HI (AWAY)': round(away_diff, 2) if pd.notna(away_diff) else None,
        'Trend Oldest 6w': round(all_diff_oldest_6w, 2) if pd.notna(all_diff_oldest_6w) else None,
        'Rounds Oldest 6w': rounds_oldest_6w,
        'Trend Recent 6w': round(all_diff_recent_6w, 2) if pd.notna(all_diff_recent_6w) else None,
        'Rounds Recent 6w': rounds_recent_6w,
        'Trend Confidence': round(trend_confidence, 2) if trend_confidence > 0 else None,
        'Weighted Trend Change': round(weighted_trend_change, 2) if weighted_trend_change is not None else None,
        'Avg Handicap Index': round(avg_handicap, 1) if pd.notna(avg_handicap) else None,
        'Consistency (ALL) StdDev': round(all_std, 2) if pd.notna(all_std) else None,
        'Adjusted StdDev': round(adjusted_std, 2) if adjusted_std is not None else None,
        'Consistency (HOME) StdDev': round(home_std, 2) if pd.notna(home_std) else None,
        'Consistency (AWAY) StdDev': round(away_std, 2) if pd.notna(away_std) else None,
        'Player Type': player_type,
        'Role': 'Pending',
        'Volatility Index': round(volatility_index, 2) if volatility_index > 0 else None,
        'Coefficient of Variation': round(coefficient_of_variation, 2) if coefficient_of_variation is not None else None,
        'Performance Rating': 'Pending',
        'Performance Score': 0,
        'Trend Rating': 'Pending',
        'Trend Score': 0,
        'Consistency Rating': 'Pending',
        'Consistency Score': 0,
        'Combined Value Score': None,
        'Preferred Location': preferred_location,
        'Location Advantage': round(location_advantage, 2) if location_advantage is not None else None,
    }


def apply_ratings(results_df, mode_label=""):
    """
    Apply distribution-based ratings to the results dataframe.
    Returns the updated dataframe with ratings applied.
    """
    prefix = f"[{mode_label}] " if mode_label else ""

    # 1. PERFORMANCE RATING
    perf_values = results_df['Avg DIFF - OPEN HI (ALL)'].dropna()

    if len(perf_values) > 0:
        perf_p20 = perf_values.quantile(0.20)
        perf_p40 = perf_values.quantile(0.40)
        perf_p60 = perf_values.quantile(0.60)
        perf_p80 = perf_values.quantile(0.80)

        print(f"\n{prefix}Performance Distribution Thresholds (Avg DIFF - OPEN HI):")
        print(f"  Excellent (bottom 20%): < {perf_p20:.2f}")
        print(f"  Good (20-40%): < {perf_p40:.2f}")
        print(f"  Average (40-60%): < {perf_p60:.2f}")
        print(f"  Below Average (60-80%): < {perf_p80:.2f}")
        print(f"  Poor (top 20%): >= {perf_p80:.2f}")

        def get_performance_rating(perf_val):
            if pd.isna(perf_val):
                return ("Unknown", 0)
            if perf_val < perf_p20:
                return ("Excellent", 10)
            elif perf_val < perf_p40:
                return ("Good", 8)
            elif perf_val < perf_p60:
                return ("Average", 6)
            elif perf_val < perf_p80:
                return ("Below Average", 4)
            else:
                return ("Poor", 2)

        results_df[['Performance Rating', 'Performance Score']] = results_df['Avg DIFF - OPEN HI (ALL)'].apply(
            lambda x: pd.Series(get_performance_rating(x))
        )

    # 2. TREND RATING
    trend_values = results_df['Weighted Trend Change'].dropna()

    if len(trend_values) > 0:
        trend_p20 = trend_values.quantile(0.20)
        trend_p40 = trend_values.quantile(0.40)
        trend_p60 = trend_values.quantile(0.60)
        trend_p80 = trend_values.quantile(0.80)

        print(f"\n{prefix}Trend Distribution Thresholds (Weighted Trend Change):")
        print(f"  Improving Strongly (bottom 20%): < {trend_p20:.2f}")
        print(f"  Improving (20-40%): < {trend_p40:.2f}")
        print(f"  Stable (40-60%): < {trend_p60:.2f}")
        print(f"  Declining (60-80%): < {trend_p80:.2f}")
        print(f"  Declining Strongly (top 20%): >= {trend_p80:.2f}")

        def get_trend_rating(trend_val):
            if pd.isna(trend_val):
                return ("Insufficient Data", 0)
            if trend_val < trend_p20:
                return ("Improving Strongly", 10)
            elif trend_val < trend_p40:
                return ("Improving", 8)
            elif trend_val < trend_p60:
                return ("Stable", 6)
            elif trend_val < trend_p80:
                return ("Declining", 4)
            else:
                return ("Declining Strongly", 2)

        results_df[['Trend Rating', 'Trend Score']] = results_df['Weighted Trend Change'].apply(
            lambda x: pd.Series(get_trend_rating(x))
        )

    # 3. CONSISTENCY RATING
    std_values = results_df['Consistency (ALL) StdDev'].dropna()

    if len(std_values) > 0:
        cons_p20 = std_values.quantile(0.20)
        cons_p40 = std_values.quantile(0.40)
        cons_p60 = std_values.quantile(0.60)
        cons_p80 = std_values.quantile(0.80)

        print(f"\n{prefix}Consistency Distribution Thresholds (using StdDev):")
        print(f"  Very Consistent (bottom 20%): < {cons_p20:.2f}")
        print(f"  Consistent (20-40%): < {cons_p40:.2f}")
        print(f"  Moderately Consistent (40-60%): < {cons_p60:.2f}")
        print(f"  Variable (60-80%): < {cons_p80:.2f}")
        print(f"  Very Variable (top 20%): >= {cons_p80:.2f}")

        def get_consistency_rating(std_val):
            if pd.isna(std_val):
                return ("Unknown", 0)
            if std_val < cons_p20:
                return ("Very Consistent", 10)
            elif std_val < cons_p40:
                return ("Consistent", 8)
            elif std_val < cons_p60:
                return ("Moderately Consistent", 6)
            elif std_val < cons_p80:
                return ("Variable", 4)
            else:
                return ("Very Variable", 2)

        results_df[['Consistency Rating', 'Consistency Score']] = results_df['Consistency (ALL) StdDev'].apply(
            lambda x: pd.Series(get_consistency_rating(x))
        )

    # 4. ROLE
    hi_values = results_df['Avg Handicap Index'].dropna()

    if len(hi_values) > 0:
        median_hi = hi_values.median()

        print(f"\n{prefix}Role Classification (Handicap Index + Consistency):")
        print(f"  Median Handicap Index: {median_hi:.1f}")
        print(f"  Gunner: HI >= {median_hi:.1f} AND Consistency Score >= 6")
        print(f"  Anchor: HI < {median_hi:.1f} AND Consistency Score >= 6")
        print(f"  Wildcard: Consistency Score < 6 (inconsistent)")

        def get_role(row):
            hi = row['Avg Handicap Index']
            cons_score = row['Consistency Score']

            if pd.isna(hi) or pd.isna(cons_score):
                return "Unknown"

            good_consistency = cons_score >= 6
            high_handicap = hi >= median_hi

            if good_consistency:
                if high_handicap:
                    return "Gunner"
                else:
                    return "Anchor"
            else:
                return "Wildcard"

        results_df['Role'] = results_df.apply(get_role, axis=1)

        # Player Type based on median Adjusted StdDev
        adj_std_values = results_df['Adjusted StdDev'].dropna()
        if len(adj_std_values) > 0:
            median_adj_std = adj_std_values.median()
            results_df['Player Type'] = results_df['Adjusted StdDev'].apply(
                lambda x: 'Steady' if pd.notna(x) and x < median_adj_std else ('Explosive' if pd.notna(x) else 'Unknown')
            )

    # 5. Combined Value Score
    # Weights: Performance 60%, Consistency 30%, Trend 10%
    def calc_combined_score(row):
        perf = row['Performance Score']
        trend = row['Trend Score']
        cons = row['Consistency Score']
        if perf > 0 and trend > 0 and cons > 0:
            return round((perf * 0.6) + (cons * 0.3) + (trend * 0.1), 1)
        return None

    results_df['Combined Value Score'] = results_df.apply(calc_combined_score, axis=1)

    return results_df


def analyze_scores(input_file, output_file, home_weight=0.7):
    """Analyze golf scores and generate metrics per player using blended HOME/ALL scoring.

    Args:
        input_file: Path to scores.csv
        output_file: Path to output analysis.csv
        home_weight: Weight for HOME stats (0.0 = ALL only, 1.0 = HOME only)
                     Default 0.7 means 70% HOME + 30% ALL to reduce impact of bad away rounds.
    """

    print("="*60)
    print(f"GOLF SCORE ANALYSIS (BLENDED: {int(home_weight*100)}% HOME + {int((1-home_weight)*100)}% ALL)")
    print("="*60)
    print(f"\nReading data from: {input_file}")

    # Read the scores CSV
    df = pd.read_csv(input_file)

    print(f"Total records loaded: {len(df)}")
    print(f"Unique players: {df['Player Name'].nunique()}")

    # Parse dates
    df['Date Played'] = pd.to_datetime(df['Date Played'], format='%d-%m-%Y %p')

    # Clean DIFF and OPEN HI values
    df['DIFF_clean'] = df['DIFF'].apply(clean_diff_value)
    df['OPEN HI_clean'] = df['OPEN HI'].astype(str).str.replace('S', '', regex=False)
    df['OPEN HI_clean'] = pd.to_numeric(df['OPEN HI_clean'], errors='coerce')

    # Calculate DIFF - OPEN HI
    df['DIFF_minus_OPEN_HI'] = df['DIFF_clean'] - df['OPEN HI_clean']

    # Determine if HOME or AWAY (HOME = KRUGERSDORP GOLF CLUB)
    df['Location'] = df['Club Played'].apply(
        lambda x: 'HOME' if x == 'KRUGERSDORP GOLF CLUB' else 'AWAY'
    )

    # Calculate date thresholds
    today = datetime.now()
    twelve_weeks_ago = today - timedelta(weeks=12)
    six_weeks_ago = today - timedelta(weeks=6)

    print(f"\nAnalyzing rounds from {twelve_weeks_ago.date()} to {today.date()}")

    # Filter to last 12 weeks - ALL rounds
    df_all = df[df['Date Played'] >= twelve_weeks_ago].copy()

    # Filter to last 12 weeks - HOME rounds only
    df_home = df[(df['Date Played'] >= twelve_weeks_ago) & (df['Location'] == 'HOME')].copy()

    print(f"ALL rounds in last 12 weeks: {len(df_all)}")
    print(f"HOME rounds in last 12 weeks: {len(df_home)}")

    # ==================== ANALYZE ALL ROUNDS ====================
    print("\n" + "="*60)
    print("ANALYZING ALL ROUNDS")
    print("="*60)

    results_all = []
    for player_name in df['Player Name'].unique():
        player_data = df_all[df_all['Player Name'] == player_name]
        result = analyze_player_data(player_name, player_data, six_weeks_ago)
        if result:
            results_all.append(result)

    results_all_df = pd.DataFrame(results_all)
    results_all_df = apply_ratings(results_all_df, "ALL")
    results_all_df = results_all_df.sort_values('Total Rounds (12 weeks)', ascending=False)

    # ==================== ANALYZE HOME-ONLY ROUNDS ====================
    print("\n" + "="*60)
    print("ANALYZING HOME-ONLY ROUNDS")
    print("="*60)

    results_home = []
    for player_name in df['Player Name'].unique():
        player_data = df_home[df_home['Player Name'] == player_name]
        result = analyze_player_data(player_name, player_data, six_weeks_ago)
        if result:
            results_home.append(result)

    results_home_df = pd.DataFrame(results_home)
    results_home_df = apply_ratings(results_home_df, "HOME")
    results_home_df = results_home_df.sort_values('Total Rounds (12 weeks)', ascending=False)

    # ==================== MERGE DATASETS ====================
    # Rename columns in HOME-only dataframe with prefix
    home_cols_to_rename = {col: f'HOME_{col}' for col in results_home_df.columns if col != 'Player Name'}
    results_home_renamed = results_home_df.rename(columns=home_cols_to_rename)

    # Merge ALL and HOME-only data on Player Name
    merged_df = results_all_df.merge(results_home_renamed, on='Player Name', how='left')

    # ==================== CALCULATE BLENDED SCORES ====================
    print(f"\n{'='*60}")
    print(f"CALCULATING BLENDED SCORES ({int(home_weight*100)}% HOME + {int((1-home_weight)*100)}% ALL)")
    print(f"{'='*60}")

    def blend_score(row):
        """Calculate blended Combined Value Score from HOME and ALL scores"""
        all_cvs = row.get('Combined Value Score')
        home_cvs = row.get('HOME_Combined Value Score')

        if pd.notna(home_cvs) and pd.notna(all_cvs):
            # Weighted blend
            blended = (home_weight * home_cvs) + ((1 - home_weight) * all_cvs)
            return round(blended, 2)
        elif pd.notna(home_cvs):
            # Only HOME available
            return home_cvs
        elif pd.notna(all_cvs):
            # Only ALL available
            return all_cvs
        return None

    # Store original scores for reference
    merged_df['ALL_Combined Value Score'] = merged_df['Combined Value Score']

    # Calculate blended score as the new main score
    merged_df['Combined Value Score'] = merged_df.apply(blend_score, axis=1)

    # Also blend the performance metric (Avg DIFF - OPEN HI)
    def blend_perf(row):
        all_perf = row.get('Avg DIFF - OPEN HI (ALL)')
        home_perf = row.get('HOME_Avg DIFF - OPEN HI (ALL)')

        if pd.notna(home_perf) and pd.notna(all_perf):
            blended = (home_weight * home_perf) + ((1 - home_weight) * all_perf)
            return round(blended, 2)
        elif pd.notna(home_perf):
            return home_perf
        elif pd.notna(all_perf):
            return all_perf
        return None

    merged_df['Blended DIFF - OPEN HI'] = merged_df.apply(blend_perf, axis=1)

    # Sort by Combined Value Score (now blended) descending
    merged_df = merged_df.sort_values('Combined Value Score', ascending=False)

    # Show blending impact for players with significant differences
    print("\nBlending impact (players with >1.0 difference between HOME and ALL CVS):")
    for _, row in merged_df.iterrows():
        all_cvs = row.get('ALL_Combined Value Score')
        home_cvs = row.get('HOME_Combined Value Score')
        blended = row.get('Combined Value Score')
        if pd.notna(all_cvs) and pd.notna(home_cvs) and abs(home_cvs - all_cvs) > 1.0:
            print(f"  {row['Player Name']:25} ALL={all_cvs:.1f}  HOME={home_cvs:.1f}  -> BLENDED={blended:.1f}")

    # Save merged CSV
    merged_df.to_csv(output_file, index=False)

    print(f"\n{'='*60}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"Output saved to: {output_file}")
    print(f"Players with ALL data: {len(results_all_df)}")
    print(f"Players with HOME data: {len(results_home_df)}")
    print(f"\nTop 10 players by Blended Combined Value Score:")

    # Show top players
    comparison_cols = ['Player Name', 'Combined Value Score', 'ALL_Combined Value Score', 'HOME_Combined Value Score']
    available_cols = [c for c in comparison_cols if c in merged_df.columns]
    print(merged_df[available_cols].head(10).to_string(index=False))

def main():
    """Main execution function"""

    # File paths
    input_file = "outputs/scores.csv"
    output_file = "outputs/analysis.csv"

    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        return

    # Run analysis
    analyze_scores(input_file, output_file)

if __name__ == "__main__":
    main()
