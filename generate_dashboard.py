"""
Golf League Dashboard Generator

Creates an interactive HTML dashboard visualizing player performance metrics:
- Performance Rating
- Trend Rating
- Consistency Rating
- Combined Value Score (Blended: 70% HOME + 30% ALL)
- Preferred Location

Usage:
    python generate_dashboard.py
"""

import pandas as pd
import json

def extract_player_data(row, prefix=''):
    """Extract player data from a row, using optional prefix for HOME-only columns"""
    p = prefix  # Shorthand

    # Helper to get value with prefix
    def get_val(col_name, default=None):
        full_col = f'{p}{col_name}' if p else col_name
        if full_col in row.index and pd.notna(row.get(full_col)):
            return row[full_col]
        return default

    return {
        'name': row['Player Name'],
        'performance_score': get_val('Performance Score', 0),
        'performance_rating': get_val('Performance Rating', 'Unknown'),
        'trend_score': get_val('Trend Score', 0),
        'trend_rating': get_val('Trend Rating', 'Unknown'),
        'trend_change': get_val('Weighted Trend Change'),
        'trend_confidence': get_val('Trend Confidence'),
        'rounds_oldest_6w': int(get_val('Rounds Oldest 6w', 0)) if get_val('Rounds Oldest 6w') else None,
        'rounds_recent_6w': int(get_val('Rounds Recent 6w', 0)) if get_val('Rounds Recent 6w') else None,
        'consistency_score': get_val('Consistency Score', 0),
        'consistency_rating': get_val('Consistency Rating', 'Unknown'),
        'stddev': get_val('Consistency (ALL) StdDev'),
        'adjusted_stddev': get_val('Adjusted StdDev'),
        'combined_score': get_val('Combined Value Score'),
        'player_type': get_val('Player Type', 'Unknown'),
        'role': get_val('Role', 'Unknown'),
        'preferred_location': get_val('Preferred Location', 'ANY'),
        'location_advantage': get_val('Location Advantage'),
        'avg_diff': get_val('Avg DIFF - OPEN HI (ALL)'),
        'total_rounds': int(get_val('Total Rounds (12 weeks)', 0)),
        'home_games_pct': get_val('Home Games %', 0),
        'home_diff': get_val('Avg DIFF - OPEN HI (HOME)'),
        'away_diff': get_val('Avg DIFF - OPEN HI (AWAY)'),
    }


def generate_dashboard(analysis_file, output_file, players_info_file="outputs/players_info.csv", players_list_file="data/players_list.csv", matchplay_file="outputs/matchplay_records.csv"):
    """Generate interactive HTML dashboard from analysis data"""
    import os

    print("="*60)
    print("GOLF LEAGUE DASHBOARD GENERATOR")
    print("="*60)
    print(f"\nReading analysis from: {analysis_file}")

    # Read analysis data
    df = pd.read_csv(analysis_file)

    # Read players_info for current HI (if available)
    current_hi_map = {}
    if os.path.exists(players_info_file):
        print(f"Reading player info from: {players_info_file}")
        df_players = pd.read_csv(players_info_file)
        for _, row in df_players.iterrows():
            if pd.notna(row.get('Current HI')):
                current_hi_map[row['Player Name']] = row['Current HI']
        print(f"Loaded current HI for {len(current_hi_map)} players")

    # Read players_list for commitment level (if available)
    commitment_map = {}
    commitment_labels = {'Full': 'Committed', 'Month-2-month': 'Ad Hoc', 'TBC': 'TBC'}
    if os.path.exists(players_list_file):
        print(f"Reading player list from: {players_list_file}")
        df_list = pd.read_csv(players_list_file)
        # Handle column name typo (Commitmnet vs Commitment)
        commit_col = 'Commitmnet' if 'Commitmnet' in df_list.columns else 'Commitment'
        for _, row in df_list.iterrows():
            if pd.notna(row.get(commit_col)):
                raw_commitment = str(row[commit_col]).strip()
                commitment_map[row['Name']] = commitment_labels.get(raw_commitment, raw_commitment)
        print(f"Loaded commitment for {len(commitment_map)} players")

    # Read matchplay records (if available)
    # Uses 'Exact Match' column to map scraped names to player list names
    matchplay_map = {}
    if os.path.exists(matchplay_file):
        print(f"Reading matchplay records from: {matchplay_file}")
        df_matchplay = pd.read_csv(matchplay_file)
        for _, row in df_matchplay.iterrows():
            # Use Exact Match column if available and not empty, otherwise skip
            exact_match = row.get('Exact Match', '')
            if pd.notna(exact_match) and str(exact_match).strip():
                player_name = str(exact_match).strip()
                matchplay_map[player_name] = {
                    'wins': int(row['Wins']),
                    'losses': int(row['Losses']),
                    'draws': int(row['Draws']),
                    'matches': int(row['Matches']),
                    'win_pct': row['Win %'],
                    'record': row['Record']
                }
        print(f"Loaded matchplay records for {len(matchplay_map)} players (using Exact Match column)")

    # Filter to players with sufficient data (has Combined Value Score for ALL)
    df_valid = df[df['Combined Value Score'].notna()].copy()

    # Sort by Combined Value Score descending
    df_valid = df_valid.sort_values('Combined Value Score', ascending=False)

    print(f"Players with complete data: {len(df_valid)}")

    # Prepare data for JavaScript - using blended scores
    players_data = []
    for _, row in df_valid.iterrows():
        player_data = extract_player_data(row, prefix='')
        player_data['current_hi'] = current_hi_map.get(row['Player Name'])
        player_data['commitment'] = commitment_map.get(row['Player Name'], 'Unknown')
        player_data['matchplay'] = matchplay_map.get(row['Player Name'])
        # Include ALL and HOME CVS for reference
        player_data['all_cvs'] = row.get('ALL_Combined Value Score') if 'ALL_Combined Value Score' in row.index else None
        player_data['home_cvs'] = row.get('HOME_Combined Value Score') if 'HOME_Combined Value Score' in row.index else None
        players_data.append(player_data)

    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KGC League - Player Analysis Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        .legend {{
            background: white;
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 20px;
            font-size: 0.8em;
            color: #64748b;
            line-height: 1.6;
        }}

        .legend-item {{
            margin-bottom: 4px;
        }}

        .legend-item:last-child {{
            margin-bottom: 0;
        }}

        .legend-item strong {{
            color: #334155;
        }}

        .cards-container {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}

        .player-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }}

        .player-card {{
            position: relative;
            border-radius: 12px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            overflow: hidden;
            background: white;
        }}

        .player-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
        }}

        /* Card header with role-based colors */
        .card-header {{
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .card-header.header-anchor {{
            background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
            border-bottom: 3px solid #059669;
        }}

        .card-header.header-gunner {{
            background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
            border-bottom: 3px solid #dc2626;
        }}

        .card-header.header-wildcard {{
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            border-bottom: 3px solid #d97706;
        }}

        .card-header.header-unknown {{
            background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
            border-bottom: 3px solid #6b7280;
        }}

        .card-body {{
            padding: 15px 20px;
        }}

        .header-left {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}

        .role-indicator {{
            font-size: 0.7em;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .role-anchor {{ color: #065f46; }}
        .role-gunner {{ color: #991b1b; }}
        .role-wildcard {{ color: #92400e; }}
        .role-unknown {{ color: #4b5563; }}

        .player-name {{
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
        }}

        .hi-circle {{
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: linear-gradient(135deg, #6b7280, #4b5563);
            color: white;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}

        .hi-label {{
            font-size: 0.5em;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            opacity: 0.8;
            margin-bottom: -2px;
        }}

        .hi-value {{
            font-weight: bold;
            font-size: 0.95em;
        }}

        .score-badge {{
            display: inline-flex;
            flex-direction: column;
            align-items: center;
            padding: 3px 12px 4px 12px;
            border-radius: 4px;
            margin: 0;
        }}

        .score-badge-label {{
            font-size: 0.4em;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            opacity: 0.85;
            margin-bottom: -1px;
        }}

        .score-badge-value {{
            font-weight: bold;
            font-size: 0.9em;
        }}

        .score-excellent {{ background: #10b981; color: white; }}
        .score-good {{ background: #3b82f6; color: white; }}
        .score-average {{ background: #f59e0b; color: white; }}
        .score-below {{ background: #ef4444; color: white; }}

        .location-badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.85em;
            font-weight: bold;
            margin-top: 5px;
        }}

        .loc-home {{ background: #dbeafe; color: #1e40af; }}
        .loc-away {{ background: #fef3c7; color: #92400e; }}
        .loc-any {{ background: #e5e7eb; color: #374151; }}

        .matchplay-record {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            padding: 6px 10px;
            border-radius: 5px;
            margin-top: 8px;
        }}

        .matchplay-label {{
            color: #94a3b8;
            font-size: 0.55em;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}

        .matchplay-stats {{
            display: flex;
            gap: 8px;
            align-items: center;
        }}

        .matchplay-wld {{
            display: flex;
            gap: 6px;
        }}

        .matchplay-stat {{
            display: flex;
            flex-direction: column;
            align-items: center;
            min-width: 20px;
        }}

        .matchplay-stat-value {{
            font-weight: bold;
            font-size: 0.85em;
            color: #64748b;
        }}

        .matchplay-stat-label {{
            font-size: 0.5em;
            color: #94a3b8;
            text-transform: uppercase;
        }}

        .matchplay-stat.win .matchplay-stat-value {{ color: #22c55e; }}
        .matchplay-stat.loss .matchplay-stat-value {{ color: #ef4444; }}
        .matchplay-stat.draw .matchplay-stat-value {{ color: #eab308; }}

        .matchplay-pct {{
            font-weight: bold;
            font-size: 0.7em;
            color: #64748b;
            background: #e2e8f0;
            padding: 2px 6px;
            border-radius: 3px;
        }}

        .no-matchplay {{
            color: #cbd5e1;
            font-size: 0.7em;
            font-style: italic;
            text-align: center;
            padding: 6px;
            background: #f8fafc;
            border-radius: 5px;
            margin-top: 8px;
        }}

        .commitment-badge {{
            position: absolute;
            top: 0;
            right: 0;
            padding: 2px 8px;
            border-radius: 0 12px 0 3px;
            font-size: 0.6em;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            background: white;
            z-index: 10;
        }}

        .commit-committed {{ color: #065f46; }}
        .commit-adhoc {{ color: #92400e; }}
        .commit-tbc {{ color: #991b1b; }}
        .commit-unknown {{ color: #374151; }}

        .stat-row {{
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
        }}

        .stat-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}

        .stat-value {{
            font-weight: bold;
            color: #333;
            font-size: 1.1em;
        }}

        .stat-rating {{
            font-size: 0.65em;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            text-align: left;
        }}

        .stat-rating.rating-excellent {{ color: #059669; }}
        .stat-rating.rating-good {{ color: #2563eb; }}
        .stat-rating.rating-average {{ color: #d97706; }}
        .stat-rating.rating-below {{ color: #dc2626; }}
        .stat-rating.rating-poor {{ color: #991b1b; }}
        .stat-rating.rating-improving {{ color: #059669; }}
        .stat-rating.rating-stable {{ color: #6b7280; }}
        .stat-rating.rating-declining {{ color: #dc2626; }}
        .stat-rating.rating-consistent {{ color: #059669; }}
        .stat-rating.rating-variable {{ color: #dc2626; }}
        .rounds-values {{
            display: flex;
            gap: 20px;
        }}

        .round-col {{
            display: flex;
            flex-direction: column;
            align-items: center;
            min-width: 40px;
        }}

        .round-label {{
            font-size: 0.65em;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #888;
        }}

        .low-rounds {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            border: 2px solid #ef4444;
            color: #ef4444;
        }}

        .rating-row {{
            margin-bottom: 10px;
        }}

        @media (max-width: 768px) {{
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}

            h1 {{
                font-size: 1.8em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="legend">
            <div class="legend-item"><strong>Role:</strong> Anchor (low HI + consistent) | Gunner (high HI + consistent) | Wildcard (inconsistent)</div>
            <div class="legend-item"><strong>HI:</strong> Current Handicap Index</div>
            <div class="legend-item"><strong>Rating:</strong> Combined Value Score (0-10) based on 60% performance + 30% consistency + 10% trend. Blended 70% HOME + 30% ALL rounds.</div>
            <div class="legend-item"><strong>Performance:</strong> Avg strokes over/under handicap (lower = better)</div>
            <div class="legend-item"><strong>Trend:</strong> Change in performance (recent 6 weeks vs oldest 6 weeks). Negative = improving.</div>
            <div class="legend-item"><strong>Consistency:</strong> Standard deviation of scores (lower = more predictable)</div>
            <div class="legend-item"><strong>Rounds:</strong> Games played in last 12 weeks. Red circle = insufficient home data (<= 6 rounds).</div>
        </div>
        <div class="cards-container">
            <div class="player-cards" id="playerCards">
                <!-- Player cards will be generated here -->
            </div>
        </div>
    </div>

    <script>
        // Player data (blended scores: 70% HOME + 30% ALL)
        const playersData = {json.dumps(players_data, indent=8)};

        // Helper to format trend change with +/- sign
        function formatTrendChange(val) {{
            if (val === null || val === undefined) return 'N/A';
            const sign = val >= 0 ? '+' : '';
            return sign + val.toFixed(2);
        }}

        // Helper to get rating color class
        function getRatingClass(rating) {{
            if (!rating) return '';
            const r = rating.toLowerCase();
            if (r.includes('excellent') || r.includes('very consistent')) return 'rating-excellent';
            if (r.includes('good') || r.includes('consistent')) return 'rating-good';
            if (r.includes('average') || r.includes('moderate') || r.includes('stable')) return 'rating-average';
            if (r.includes('improving')) return 'rating-improving';
            if (r.includes('declining') || r.includes('variable') || r.includes('below') || r.includes('poor')) return 'rating-declining';
            return '';
        }}

        // Helper to calculate home/away rounds
        function getHomeAwayRounds(player) {{
            const total = player.total_rounds || 0;
            const homePct = player.home_games_pct || 0;
            const homeRounds = Math.round(total * homePct / 100);
            const awayRounds = total - homeRounds;
            return {{ home: homeRounds, away: awayRounds }};
        }}

        // Helper to get commitment class
        function getCommitmentClass(commitment) {{
            if (!commitment) return 'commit-unknown';
            const c = commitment.toLowerCase();
            if (c === 'committed') return 'commit-committed';
            if (c === 'ad hoc') return 'commit-adhoc';
            if (c === 'tbc') return 'commit-tbc';
            return 'commit-unknown';
        }}

        // Generate Player Cards
        function generatePlayerCards(players) {{
            const container = document.getElementById('playerCards');

            if (players.length === 0) {{
                container.innerHTML = '<p style="color: #666; text-align: center; padding: 40px;">No players match the current filter.</p>';
                return;
            }}

            container.innerHTML = players.map(player => `
                <div class="player-card" data-role="${{player.role}}" data-combined="${{player.combined_score}}" data-location="${{player.preferred_location}}">
                    <span class="commitment-badge ${{getCommitmentClass(player.commitment)}}">
                        ${{player.commitment || 'Unknown'}}
                    </span>
                    <div class="card-header header-${{player.role ? player.role.toLowerCase() : 'unknown'}}">
                        <div class="header-left">
                            <span class="role-indicator role-${{player.role ? player.role.toLowerCase() : 'unknown'}}">
                                ${{player.role || 'Unknown'}}
                            </span>
                            <div class="player-name">
                                ${{player.name}}
                            </div>
                        </div>
                        <div class="hi-circle" title="Current Handicap Index">
                            <span class="hi-label">HI</span>
                            <span class="hi-value">${{player.current_hi != null ? player.current_hi : '-'}}</span>
                        </div>
                    </div>

                    <div class="card-body">
                        <div class="rating-row">
                            <span class="score-badge ${{
                                player.combined_score >= 8 ? 'score-excellent' :
                                player.combined_score >= 6 ? 'score-good' :
                                player.combined_score >= 5 ? 'score-average' : 'score-below'
                            }}">
                                <span class="score-badge-label">Rating</span>
                                <span class="score-badge-value">${{player.combined_score ? player.combined_score.toFixed(1) : 'N/A'}}</span>
                            </span>
                        </div>

                        <div class="stat-row">
                            <div class="stat-top">
                                <span class="stat-label">Performance</span>
                                <span class="stat-value">${{player.avg_diff ? player.avg_diff.toFixed(2) : 'N/A'}}</span>
                            </div>
                            <div class="stat-rating ${{getRatingClass(player.performance_rating)}}">${{player.performance_rating}}</div>
                        </div>

                        <div class="stat-row">
                            <div class="stat-top">
                                <span class="stat-label">Trend</span>
                                <span class="stat-value">${{formatTrendChange(player.trend_change)}}</span>
                            </div>
                            <div class="stat-rating ${{getRatingClass(player.trend_rating)}}">${{player.trend_rating}}</div>
                        </div>

                        <div class="stat-row">
                            <div class="stat-top">
                                <span class="stat-label">Consistency</span>
                                <span class="stat-value">${{player.stddev ? player.stddev.toFixed(2) : 'N/A'}}</span>
                            </div>
                            <div class="stat-rating ${{getRatingClass(player.consistency_rating)}}">${{player.consistency_rating}}</div>
                        </div>

                        <div class="stat-row">
                            <div class="stat-top">
                                <span class="stat-label">Rounds</span>
                                <div class="rounds-values">
                                    <div class="round-col"><span class="stat-value ${{getHomeAwayRounds(player).home <= 6 ? 'low-rounds' : ''}}">${{getHomeAwayRounds(player).home}}</span><span class="round-label">HOME</span></div>
                                    <div class="round-col"><span class="stat-value">${{getHomeAwayRounds(player).away}}</span><span class="round-label">AWAY</span></div>
                                </div>
                            </div>
                        </div>

                        ${{player.matchplay ? `
                        <div class="matchplay-record">
                            <span class="matchplay-label">All-Time Match Play</span>
                            <div class="matchplay-stats">
                                <div class="matchplay-wld">
                                    <div class="matchplay-stat win">
                                        <span class="matchplay-stat-value">${{player.matchplay.wins}}</span>
                                        <span class="matchplay-stat-label">W</span>
                                    </div>
                                    <div class="matchplay-stat loss">
                                        <span class="matchplay-stat-value">${{player.matchplay.losses}}</span>
                                        <span class="matchplay-stat-label">L</span>
                                    </div>
                                    <div class="matchplay-stat draw">
                                        <span class="matchplay-stat-value">${{player.matchplay.draws}}</span>
                                        <span class="matchplay-stat-label">D</span>
                                    </div>
                                </div>
                                <span class="matchplay-pct">${{player.matchplay.win_pct}}</span>
                            </div>
                        </div>
                        ` : `<div class="no-matchplay">No match play history</div>`}}
                    </div>
                </div>
            `).join('');
        }}

        // Initialize with all players
        generatePlayerCards(playersData);
    </script>
</body>
</html>"""

    # Write HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n{'='*60}")
    print("DASHBOARD GENERATED")
    print(f"{'='*60}")
    print(f"Output saved to: {output_file}")
    print(f"Open this file in your web browser to view the dashboard")

def main():
    """Main execution function"""

    analysis_file = "outputs/analysis.csv"
    output_file = "outputs/dashboard.html"

    generate_dashboard(analysis_file, output_file)

if __name__ == "__main__":
    main()
