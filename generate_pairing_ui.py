"""
KGC League Pairing UI Generator
================================
Generates an interactive HTML page where you can drag and drop
player cards to create pairs manually.

Features:
- Drag players from pool to create pairs
- Drag complete pairs between HOME, AWAY, and RESERVE sections
- 4 HOME pairs + 1 HOME reserve
- 4 AWAY pairs + 1 AWAY reserve
- 2 General reserve slots
"""

import pandas as pd
import json
import os


def load_data():
    """Load all required data files"""

    # Load analysis
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
                'wins': int(row['Wins']),
                'losses': int(row['Losses']),
                'draws': int(row['Draws']),
                'matches': int(row['Matches']),
                'win_pct': float(row['Win %'].replace('%', '')) if isinstance(row['Win %'], str) else float(row['Win %']),
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

    row = analysis_df[analysis_df['Player Name'] == name]
    if not row.empty:
        row = row.iloc[0]
        player['cvs'] = float(row.get('Combined Value Score')) if pd.notna(row.get('Combined Value Score')) else None
        player['role'] = row.get('Role', 'Unknown')
        player['consistency_score'] = float(row.get('Consistency Score')) if pd.notna(row.get('Consistency Score')) else 0

        # Calculate home rounds
        total_rounds = row.get('Total Rounds (12 weeks)', 0) or 0
        home_pct = row.get('Home Games %', 0) or 0
        player['total_rounds'] = int(total_rounds)
        player['home_rounds'] = int(round(total_rounds * home_pct / 100)) if home_pct > 0 else 0
    else:
        player['cvs'] = None
        player['role'] = 'Unknown'
        player['consistency_score'] = 0
        player['home_rounds'] = 0
        player['total_rounds'] = 0

    player['commitment'] = commitment_map.get(name, 'Unknown')
    player['matchplay'] = matchplay_map.get(name)
    player['hi'] = float(hi_map.get(name, 15))
    player['is_wildcard'] = player['consistency_score'] < 6 if player['consistency_score'] else False

    return player


def generate_pairing_ui():
    """Generate interactive pairing UI"""

    print("Loading player data...")
    analysis, commitment_map, matchplay_map, hi_map = load_data()

    # Get all players with data
    all_players = []
    for name in commitment_map.keys():
        player = get_player_data(name, analysis, commitment_map, matchplay_map, hi_map)
        if player['cvs'] is not None:
            all_players.append(player)

    # Sort by CVS
    all_players.sort(key=lambda p: p['cvs'] or 0, reverse=True)

    # Separate by commitment
    committed = [p for p in all_players if p['commitment'] == 'Full']
    monthly = [p for p in all_players if p['commitment'] == 'Month-2-month']
    tbc = [p for p in all_players if p['commitment'] == 'TBC']

    # Convert to JSON for JavaScript
    players_json = json.dumps(all_players, default=str)

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KGC League - Pairing Builder</title>
    <style>
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }}

        .container {{
            max-width: 1800px;
            margin: 0 auto;
        }}

        h1 {{
            color: white;
            text-align: center;
            margin-bottom: 10px;
            font-size: 2em;
        }}

        .subtitle {{
            color: rgba(255,255,255,0.8);
            text-align: center;
            margin-bottom: 20px;
            font-size: 0.9em;
        }}

        .main-layout {{
            display: grid;
            grid-template-columns: 280px 1fr;
            gap: 20px;
        }}

        .player-pool {{
            background: white;
            border-radius: 12px;
            padding: 15px;
            max-height: calc(100vh - 140px);
            overflow-y: auto;
        }}

        .pool-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e5e7eb;
        }}

        .pool-title {{
            font-weight: bold;
            color: #1e3a5f;
        }}

        .pool-count {{
            background: #3b82f6;
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.8em;
        }}

        .filter-tabs {{
            display: flex;
            gap: 5px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}

        .filter-tab {{
            padding: 5px 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.75em;
            background: #e5e7eb;
            color: #374151;
            transition: all 0.2s;
        }}

        .filter-tab:hover {{
            background: #d1d5db;
        }}

        .filter-tab.active {{
            background: #3b82f6;
            color: white;
        }}

        .player-card {{
            background: #f8fafc;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 8px;
            cursor: grab;
            transition: all 0.2s;
            position: relative;
        }}

        .player-card:hover {{
            border-color: #3b82f6;
            transform: translateX(3px);
            box-shadow: 0 2px 8px rgba(59, 130, 246, 0.2);
        }}

        .player-card.dragging {{
            opacity: 0.5;
            cursor: grabbing;
        }}

        .player-card.committed {{
            border-left: 4px solid #10b981;
        }}

        .player-card.monthly {{
            border-left: 4px solid #f59e0b;
        }}

        .player-card.tbc {{
            border-left: 4px solid #6b7280;
        }}

        .player-name {{
            font-weight: bold;
            font-size: 0.9em;
            color: #1e3a5f;
            margin-bottom: 5px;
        }}

        .player-stats {{
            display: flex;
            gap: 10px;
            font-size: 0.75em;
            color: #64748b;
        }}

        .stat {{
            display: flex;
            align-items: center;
            gap: 3px;
        }}

        .stat-label {{
            color: #94a3b8;
        }}

        .stat-value {{
            font-weight: 600;
        }}

        .stat-value.excellent {{ color: #10b981; }}
        .stat-value.good {{ color: #3b82f6; }}
        .stat-value.average {{ color: #f59e0b; }}
        .stat-value.below {{ color: #ef4444; }}

        .role-badge {{
            position: absolute;
            top: 5px;
            right: 5px;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.6em;
            font-weight: bold;
            text-transform: uppercase;
        }}

        .role-anchor {{ background: #dbeafe; color: #1e40af; }}
        .role-gunner {{ background: #dcfce7; color: #166534; }}
        .role-wildcard {{ background: #fef3c7; color: #92400e; }}

        .pairing-area {{
            background: white;
            border-radius: 12px;
            padding: 20px;
        }}

        .pairing-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}

        .pairing-title {{
            font-weight: bold;
            color: #1e3a5f;
            font-size: 1.2em;
        }}

        .actions {{
            display: flex;
            gap: 10px;
        }}

        .btn {{
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85em;
            font-weight: 500;
            transition: all 0.2s;
        }}

        .btn-primary {{ background: #3b82f6; color: white; }}
        .btn-primary:hover {{ background: #2563eb; }}
        .btn-secondary {{ background: #e5e7eb; color: #374151; }}
        .btn-secondary:hover {{ background: #d1d5db; }}
        .btn-danger {{ background: #ef4444; color: white; }}
        .btn-danger:hover {{ background: #dc2626; }}

        .teams-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}

        .team-section {{
            background: #f8fafc;
            border-radius: 10px;
            padding: 15px;
        }}

        .team-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e2e8f0;
        }}

        .team-title {{
            font-weight: bold;
            font-size: 1.1em;
        }}

        .team-home .team-title {{ color: #166534; }}
        .team-away .team-title {{ color: #b45309; }}
        .team-reserve .team-title {{ color: #6b7280; }}

        .team-cvs {{
            font-size: 0.85em;
            padding: 3px 8px;
            border-radius: 5px;
        }}

        .team-home .team-cvs {{ background: #dcfce7; color: #166534; }}
        .team-away .team-cvs {{ background: #fef3c7; color: #92400e; }}
        .team-reserve .team-cvs {{ background: #f3f4f6; color: #6b7280; }}

        .pairs-container {{
            min-height: 100px;
        }}

        .pair-slot {{
            background: white;
            border: 2px dashed #cbd5e1;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 10px;
            min-height: 80px;
            display: flex;
            gap: 10px;
            transition: all 0.2s;
            cursor: default;
        }}

        .pair-slot.drag-over {{
            border-color: #3b82f6;
            background: #eff6ff;
        }}

        .pair-slot.complete {{
            border-style: solid;
            border-color: #10b981;
            background: #f0fdf4;
            cursor: grab;
        }}

        .pair-slot.complete.dragging {{
            opacity: 0.5;
        }}

        .pair-slot.is-reserve {{
            border-color: #9ca3af;
        }}

        .pair-slot.is-reserve.complete {{
            border-color: #6b7280;
            background: #f9fafb;
        }}

        .pair-number {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 30px;
            height: 30px;
            background: #e2e8f0;
            border-radius: 50%;
            font-weight: bold;
            font-size: 0.9em;
            color: #64748b;
            flex-shrink: 0;
        }}

        .pair-slot.complete .pair-number {{
            background: #10b981;
            color: white;
        }}

        .pair-slot.is-reserve .pair-number {{
            background: #9ca3af;
        }}

        .pair-slot.is-reserve.complete .pair-number {{
            background: #6b7280;
            color: white;
        }}

        .pair-players {{
            display: flex;
            gap: 10px;
            flex: 1;
        }}

        .player-drop-zone {{
            flex: 1;
            min-height: 60px;
            border: 2px dashed #e2e8f0;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #94a3b8;
            font-size: 0.8em;
            transition: all 0.2s;
        }}

        .player-drop-zone.drag-over {{
            border-color: #3b82f6;
            background: #eff6ff;
            color: #3b82f6;
        }}

        .player-drop-zone.has-player {{
            border: none;
            padding: 0;
        }}

        .paired-player {{
            background: #f1f5f9;
            border-radius: 6px;
            padding: 8px;
            width: 100%;
            position: relative;
        }}

        .paired-player .remove-btn {{
            position: absolute;
            top: 3px;
            right: 3px;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            border: none;
            background: #ef4444;
            color: white;
            cursor: pointer;
            font-size: 0.7em;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: opacity 0.2s;
        }}

        .paired-player:hover .remove-btn {{
            opacity: 1;
        }}

        .pair-stats {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 0 10px;
            min-width: 60px;
        }}

        .pair-cvs {{
            font-weight: bold;
            font-size: 1.1em;
            color: #1e3a5f;
        }}

        .pair-spread {{
            font-size: 0.7em;
            color: #64748b;
        }}

        .reserves-section {{
            margin-top: 20px;
            grid-column: span 2;
        }}

        .reserves-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr 2fr;
            gap: 15px;
        }}

        .reserve-column {{
            background: #f8fafc;
            border-radius: 10px;
            padding: 15px;
        }}

        .reserve-column.general {{
            background: #f1f5f9;
        }}

        .reserve-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 2px solid #e2e8f0;
        }}

        .reserve-title {{
            font-weight: bold;
            font-size: 0.95em;
            color: #6b7280;
        }}

        .general-reserves-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}

        .summary-bar {{
            background: #1e3a5f;
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            margin-top: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .summary-stats {{
            display: flex;
            gap: 30px;
        }}

        .summary-stat {{
            text-align: center;
        }}

        .summary-value {{
            font-size: 1.5em;
            font-weight: bold;
        }}

        .summary-label {{
            font-size: 0.75em;
            opacity: 0.8;
        }}

        .export-area {{
            margin-top: 15px;
            padding: 15px;
            background: #f8fafc;
            border-radius: 8px;
            display: none;
        }}

        .export-area.visible {{
            display: block;
        }}

        .export-area textarea {{
            width: 100%;
            height: 150px;
            font-family: monospace;
            font-size: 0.8em;
            padding: 10px;
            border: 1px solid #e2e8f0;
            border-radius: 5px;
            resize: vertical;
        }}

        .hidden {{
            display: none !important;
        }}

        .drag-hint {{
            font-size: 0.75em;
            color: #94a3b8;
            text-align: center;
            margin-top: 5px;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>KGC League Pairing Builder</h1>
        <p class="subtitle">Drag players to create pairs, then drag complete pairs between HOME, AWAY, and RESERVES</p>

        <div class="main-layout">
            <div class="player-pool">
                <div class="pool-header">
                    <span class="pool-title">Available Players</span>
                    <span class="pool-count" id="poolCount">0</span>
                </div>

                <div class="filter-tabs">
                    <button class="filter-tab active" data-filter="all">All</button>
                    <button class="filter-tab" data-filter="committed">Committed</button>
                    <button class="filter-tab" data-filter="monthly">Monthly</button>
                    <button class="filter-tab" data-filter="anchor">Anchors</button>
                    <button class="filter-tab" data-filter="gunner">Gunners</button>
                    <button class="filter-tab" data-filter="wildcard">Wildcards</button>
                </div>

                <div id="playerPool"></div>
            </div>

            <div class="pairing-area">
                <div class="pairing-header">
                    <span class="pairing-title">Team Pairings</span>
                    <div class="actions">
                        <button class="btn btn-secondary" onclick="clearAll()">Clear All</button>
                        <button class="btn btn-secondary" onclick="autoFill()">Auto-Fill</button>
                        <button class="btn btn-primary" onclick="exportPairings()">Export CSV</button>
                    </div>
                </div>

                <div class="teams-grid">
                    <div class="team-section team-home">
                        <div class="team-header">
                            <span class="team-title">HOME Team (Pairs 1-4)</span>
                            <span class="team-cvs" id="homeCvs">CVS: 0</span>
                        </div>
                        <div class="pairs-container" id="homePairs" data-section="home"></div>
                        <p class="drag-hint">Drag complete pairs here</p>
                    </div>

                    <div class="team-section team-away">
                        <div class="team-header">
                            <span class="team-title">AWAY Team (Pairs 5-8)</span>
                            <span class="team-cvs" id="awayCvs">CVS: 0</span>
                        </div>
                        <div class="pairs-container" id="awayPairs" data-section="away"></div>
                        <p class="drag-hint">Drag complete pairs here</p>
                    </div>

                    <div class="reserves-section">
                        <div class="reserves-grid">
                            <div class="reserve-column">
                                <div class="reserve-header">
                                    <span class="reserve-title">HOME Reserve</span>
                                </div>
                                <div class="pairs-container" id="homeReserve" data-section="homeReserve"></div>
                            </div>

                            <div class="reserve-column">
                                <div class="reserve-header">
                                    <span class="reserve-title">AWAY Reserve</span>
                                </div>
                                <div class="pairs-container" id="awayReserve" data-section="awayReserve"></div>
                            </div>

                            <div class="reserve-column general">
                                <div class="reserve-header">
                                    <span class="reserve-title">General Reserves</span>
                                </div>
                                <div class="general-reserves-container">
                                    <div class="pairs-container" id="generalReserve1" data-section="generalReserve1"></div>
                                    <div class="pairs-container" id="generalReserve2" data-section="generalReserve2"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="summary-bar">
                    <div class="summary-stats">
                        <div class="summary-stat">
                            <div class="summary-value" id="totalPairs">0/8</div>
                            <div class="summary-label">Playing Pairs</div>
                        </div>
                        <div class="summary-stat">
                            <div class="summary-value" id="reservePairs">0</div>
                            <div class="summary-label">Reserve Pairs</div>
                        </div>
                        <div class="summary-stat">
                            <div class="summary-value" id="totalCvs">0</div>
                            <div class="summary-label">Total CVS</div>
                        </div>
                        <div class="summary-stat">
                            <div class="summary-value" id="committedCount">0</div>
                            <div class="summary-label">Committed Players</div>
                        </div>
                    </div>
                </div>

                <div class="export-area" id="exportArea">
                    <textarea id="exportText" readonly></textarea>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Player data from Python
        const allPlayers = {players_json};

        // State - sections with their pairs
        let availablePlayers = [...allPlayers];
        let sections = {{
            home: Array(4).fill(null).map(() => ({{ anchor: null, gunner: null }})),
            away: Array(4).fill(null).map(() => ({{ anchor: null, gunner: null }})),
            homeReserve: [{{ anchor: null, gunner: null }}],
            awayReserve: [{{ anchor: null, gunner: null }}],
            generalReserve1: [{{ anchor: null, gunner: null }}],
            generalReserve2: [{{ anchor: null, gunner: null }}]
        }};

        let currentFilter = 'all';
        let draggedPlayer = null;
        let draggedPair = null;

        // Initialize
        function init() {{
            renderPlayerPool();
            renderAllSections();
            updateStats();
            setupSectionDropZones();

            // Filter tabs
            document.querySelectorAll('.filter-tab').forEach(tab => {{
                tab.addEventListener('click', () => {{
                    document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
                    tab.classList.add('active');
                    currentFilter = tab.dataset.filter;
                    renderPlayerPool();
                }});
            }});
        }}

        // Setup section drop zones for pair dragging
        function setupSectionDropZones() {{
            document.querySelectorAll('.pairs-container').forEach(container => {{
                container.addEventListener('dragover', (e) => {{
                    if (draggedPair) {{
                        e.preventDefault();
                        container.style.background = '#eff6ff';
                    }}
                }});

                container.addEventListener('dragleave', () => {{
                    container.style.background = '';
                }});

                container.addEventListener('drop', (e) => {{
                    e.preventDefault();
                    container.style.background = '';

                    if (draggedPair) {{
                        const targetSection = container.dataset.section;
                        movePairToSection(draggedPair.section, draggedPair.index, targetSection);
                    }}
                }});
            }});
        }}

        // Move pair from one section to another
        function movePairToSection(fromSection, fromIndex, toSection) {{
            const pair = sections[fromSection][fromIndex];
            if (!pair.anchor || !pair.gunner) return;

            // Find empty slot in target section
            const targetSlots = sections[toSection];
            let emptyIndex = targetSlots.findIndex(p => !p.anchor && !p.gunner);

            if (emptyIndex === -1) {{
                // No empty slot, swap with first slot
                emptyIndex = 0;
                const swapPair = targetSlots[emptyIndex];

                // Move existing pair to source
                sections[fromSection][fromIndex] = {{ ...swapPair }};
            }} else {{
                // Clear source
                sections[fromSection][fromIndex] = {{ anchor: null, gunner: null }};
            }}

            // Move pair to target
            sections[toSection][emptyIndex] = {{ ...pair }};

            renderAllSections();
            updateStats();
        }}

        // Render player pool
        function renderPlayerPool() {{
            const pool = document.getElementById('playerPool');
            pool.innerHTML = '';

            let filtered = availablePlayers;

            if (currentFilter === 'committed') {{
                filtered = availablePlayers.filter(p => p.commitment === 'Full');
            }} else if (currentFilter === 'monthly') {{
                filtered = availablePlayers.filter(p => p.commitment === 'Month-2-month');
            }} else if (currentFilter === 'anchor') {{
                filtered = availablePlayers.filter(p => p.role === 'Anchor');
            }} else if (currentFilter === 'gunner') {{
                filtered = availablePlayers.filter(p => p.role === 'Gunner');
            }} else if (currentFilter === 'wildcard') {{
                filtered = availablePlayers.filter(p => p.role === 'Wildcard' || p.is_wildcard);
            }}

            filtered.forEach(player => {{
                const card = createPlayerCard(player);
                pool.appendChild(card);
            }});

            document.getElementById('poolCount').textContent = filtered.length;
        }}

        // Create player card
        function createPlayerCard(player) {{
            const card = document.createElement('div');
            card.className = `player-card ${{player.commitment === 'Full' ? 'committed' : player.commitment === 'Month-2-month' ? 'monthly' : 'tbc'}}`;
            card.draggable = true;
            card.dataset.playerName = player.name;

            const cvsClass = player.cvs >= 8 ? 'excellent' : player.cvs >= 6 ? 'good' : player.cvs >= 5 ? 'average' : 'below';
            const roleClass = player.role === 'Anchor' ? 'role-anchor' : player.role === 'Gunner' ? 'role-gunner' : 'role-wildcard';
            const mp = player.matchplay ? player.matchplay.record : 'New';

            card.innerHTML = `
                <span class="role-badge ${{roleClass}}">${{player.role}}</span>
                <div class="player-name">${{player.name}}</div>
                <div class="player-stats">
                    <div class="stat">
                        <span class="stat-label">HI:</span>
                        <span class="stat-value">${{player.hi.toFixed(1)}}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">CVS:</span>
                        <span class="stat-value ${{cvsClass}}">${{player.cvs ? player.cvs.toFixed(1) : 'N/A'}}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">MP:</span>
                        <span class="stat-value">${{mp}}</span>
                    </div>
                </div>
            `;

            // Drag events
            card.addEventListener('dragstart', (e) => {{
                draggedPlayer = player;
                draggedPair = null;
                card.classList.add('dragging');
                e.dataTransfer.effectAllowed = 'move';
            }});

            card.addEventListener('dragend', () => {{
                card.classList.remove('dragging');
                draggedPlayer = null;
            }});

            return card;
        }}

        // Render all sections
        function renderAllSections() {{
            renderSection('home', 'homePairs', 1);
            renderSection('away', 'awayPairs', 5);
            renderSection('homeReserve', 'homeReserve', 'R1', true);
            renderSection('awayReserve', 'awayReserve', 'R2', true);
            renderSection('generalReserve1', 'generalReserve1', 'R3', true);
            renderSection('generalReserve2', 'generalReserve2', 'R4', true);
        }}

        // Render a section's pairs
        function renderSection(sectionKey, containerId, startNum, isReserve = false) {{
            const container = document.getElementById(containerId);
            container.innerHTML = '';

            sections[sectionKey].forEach((pair, i) => {{
                const slot = createPairSlot(sectionKey, i, typeof startNum === 'number' ? startNum + i : startNum, isReserve);
                container.appendChild(slot);
            }});
        }}

        // Create pair slot
        function createPairSlot(section, index, displayNum, isReserve = false) {{
            const pair = sections[section][index];
            const isComplete = pair.anchor && pair.gunner;

            const slot = document.createElement('div');
            slot.className = `pair-slot ${{isComplete ? 'complete' : ''}} ${{isReserve ? 'is-reserve' : ''}}`;
            slot.dataset.section = section;
            slot.dataset.index = index;

            const pairCvs = (pair.anchor?.cvs || 0) + (pair.gunner?.cvs || 0);
            const hiSpread = pair.anchor && pair.gunner ? Math.abs(pair.anchor.hi - pair.gunner.hi).toFixed(1) : '-';

            slot.innerHTML = `
                <div class="pair-number">${{displayNum}}</div>
                <div class="pair-players">
                    <div class="player-drop-zone ${{pair.anchor ? 'has-player' : ''}}" data-section="${{section}}" data-index="${{index}}" data-role="anchor">
                        ${{pair.anchor ? createPairedPlayerHTML(pair.anchor, section, index, 'anchor') : 'Drop Anchor'}}
                    </div>
                    <div class="player-drop-zone ${{pair.gunner ? 'has-player' : ''}}" data-section="${{section}}" data-index="${{index}}" data-role="gunner">
                        ${{pair.gunner ? createPairedPlayerHTML(pair.gunner, section, index, 'gunner') : 'Drop Gunner'}}
                    </div>
                </div>
                <div class="pair-stats">
                    <div class="pair-cvs">${{isComplete ? pairCvs.toFixed(1) : '-'}}</div>
                    <div class="pair-spread">Spread: ${{hiSpread}}</div>
                </div>
            `;

            // Make complete pairs draggable
            if (isComplete) {{
                slot.draggable = true;

                slot.addEventListener('dragstart', (e) => {{
                    draggedPair = {{ section, index }};
                    draggedPlayer = null;
                    slot.classList.add('dragging');
                    e.dataTransfer.effectAllowed = 'move';
                }});

                slot.addEventListener('dragend', () => {{
                    slot.classList.remove('dragging');
                    draggedPair = null;
                }});
            }}

            // Drop zone events for players
            slot.querySelectorAll('.player-drop-zone').forEach(zone => {{
                zone.addEventListener('dragover', (e) => {{
                    if (draggedPlayer) {{
                        e.preventDefault();
                        zone.classList.add('drag-over');
                    }}
                }});

                zone.addEventListener('dragleave', () => {{
                    zone.classList.remove('drag-over');
                }});

                zone.addEventListener('drop', (e) => {{
                    e.preventDefault();
                    e.stopPropagation();
                    zone.classList.remove('drag-over');

                    if (draggedPlayer) {{
                        const sec = zone.dataset.section;
                        const idx = parseInt(zone.dataset.index);
                        const role = zone.dataset.role;
                        addPlayerToPair(draggedPlayer, sec, idx, role);
                    }}
                }});
            }});

            return slot;
        }}

        // Create paired player HTML
        function createPairedPlayerHTML(player, section, index, role) {{
            const cvsClass = player.cvs >= 8 ? 'excellent' : player.cvs >= 6 ? 'good' : player.cvs >= 5 ? 'average' : 'below';

            return `
                <div class="paired-player">
                    <button class="remove-btn" onclick="event.stopPropagation(); removeFromPair('${{section}}', ${{index}}, '${{role}}')">&times;</button>
                    <div class="player-name" style="font-size: 0.85em;">${{player.name}}</div>
                    <div class="player-stats">
                        <div class="stat">
                            <span class="stat-label">HI:</span>
                            <span class="stat-value">${{player.hi.toFixed(1)}}</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">CVS:</span>
                            <span class="stat-value ${{cvsClass}}">${{player.cvs ? player.cvs.toFixed(1) : '-'}}</span>
                        </div>
                    </div>
                </div>
            `;
        }}

        // Add player to pair
        function addPlayerToPair(player, section, index, role) {{
            // Remove from available
            availablePlayers = availablePlayers.filter(p => p.name !== player.name);

            // If slot already has a player, return that player to pool
            if (sections[section][index][role]) {{
                availablePlayers.push(sections[section][index][role]);
                availablePlayers.sort((a, b) => (b.cvs || 0) - (a.cvs || 0));
            }}

            // Add to pair
            sections[section][index][role] = player;

            // Re-render
            renderPlayerPool();
            renderAllSections();
            updateStats();
        }}

        // Remove from pair
        function removeFromPair(section, index, role) {{
            const player = sections[section][index][role];
            if (player) {{
                availablePlayers.push(player);
                availablePlayers.sort((a, b) => (b.cvs || 0) - (a.cvs || 0));
                sections[section][index][role] = null;

                renderPlayerPool();
                renderAllSections();
                updateStats();
            }}
        }}

        // Update stats
        function updateStats() {{
            let playingPairs = 0;
            let reservePairs = 0;
            let totalCvs = 0;
            let homeCvs = 0;
            let awayCvs = 0;
            let committed = 0;

            // Count playing pairs (home + away)
            ['home', 'away'].forEach(sec => {{
                sections[sec].forEach((pair, i) => {{
                    if (pair.anchor && pair.gunner) {{
                        playingPairs++;
                        const pairCvs = (pair.anchor.cvs || 0) + (pair.gunner.cvs || 0);
                        totalCvs += pairCvs;

                        if (sec === 'home') homeCvs += pairCvs;
                        else awayCvs += pairCvs;

                        if (pair.anchor.commitment === 'Full') committed++;
                        if (pair.gunner.commitment === 'Full') committed++;
                    }}
                }});
            }});

            // Count reserve pairs
            ['homeReserve', 'awayReserve', 'generalReserve1', 'generalReserve2'].forEach(sec => {{
                sections[sec].forEach(pair => {{
                    if (pair.anchor && pair.gunner) {{
                        reservePairs++;
                        if (pair.anchor.commitment === 'Full') committed++;
                        if (pair.gunner.commitment === 'Full') committed++;
                    }}
                }});
            }});

            document.getElementById('totalPairs').textContent = `${{playingPairs}}/8`;
            document.getElementById('reservePairs').textContent = reservePairs;
            document.getElementById('totalCvs').textContent = totalCvs.toFixed(1);
            document.getElementById('committedCount').textContent = committed;
            document.getElementById('homeCvs').textContent = `CVS: ${{homeCvs.toFixed(1)}}`;
            document.getElementById('awayCvs').textContent = `CVS: ${{awayCvs.toFixed(1)}}`;
        }}

        // Clear all
        function clearAll() {{
            Object.keys(sections).forEach(sec => {{
                sections[sec].forEach(pair => {{
                    if (pair.anchor) availablePlayers.push(pair.anchor);
                    if (pair.gunner) availablePlayers.push(pair.gunner);
                }});
            }});

            availablePlayers.sort((a, b) => (b.cvs || 0) - (a.cvs || 0));

            sections = {{
                home: Array(4).fill(null).map(() => ({{ anchor: null, gunner: null }})),
                away: Array(4).fill(null).map(() => ({{ anchor: null, gunner: null }})),
                homeReserve: [{{ anchor: null, gunner: null }}],
                awayReserve: [{{ anchor: null, gunner: null }}],
                generalReserve1: [{{ anchor: null, gunner: null }}],
                generalReserve2: [{{ anchor: null, gunner: null }}]
            }};

            renderPlayerPool();
            renderAllSections();
            updateStats();
        }}

        // Auto-fill using best anchor + best gunner strategy
        function autoFill() {{
            // Sort available by HI
            const sorted = [...availablePlayers].sort((a, b) => a.hi - b.hi);
            const mid = Math.floor(sorted.length / 2);

            let anchors = sorted.slice(0, mid).sort((a, b) => (b.cvs || 0) - (a.cvs || 0));
            let gunners = sorted.slice(mid).sort((a, b) => (b.cvs || 0) - (a.cvs || 0));

            // Fill playing pairs first (home then away)
            ['home', 'away'].forEach(sec => {{
                sections[sec].forEach((pair, i) => {{
                    if (!pair.anchor && anchors.length > 0) {{
                        sections[sec][i].anchor = anchors.shift();
                        availablePlayers = availablePlayers.filter(p => p.name !== sections[sec][i].anchor.name);
                    }}
                    if (!pair.gunner && gunners.length > 0) {{
                        sections[sec][i].gunner = gunners.shift();
                        availablePlayers = availablePlayers.filter(p => p.name !== sections[sec][i].gunner.name);
                    }}
                }});
            }});

            // Fill reserves
            ['homeReserve', 'awayReserve', 'generalReserve1', 'generalReserve2'].forEach(sec => {{
                sections[sec].forEach((pair, i) => {{
                    if (!pair.anchor && anchors.length > 0) {{
                        sections[sec][i].anchor = anchors.shift();
                        availablePlayers = availablePlayers.filter(p => p.name !== sections[sec][i].anchor.name);
                    }}
                    if (!pair.gunner && gunners.length > 0) {{
                        sections[sec][i].gunner = gunners.shift();
                        availablePlayers = availablePlayers.filter(p => p.name !== sections[sec][i].gunner.name);
                    }}
                }});
            }});

            renderPlayerPool();
            renderAllSections();
            updateStats();
        }}

        // Export pairings
        function exportPairings() {{
            let csv = 'Pair,Location,Status,Pair CVS,Anchor,Anchor HI,Anchor CVS,Anchor Commitment,Gunner,Gunner HI,Gunner CVS,Gunner Commitment,HI Spread\\n';

            let pairNum = 1;

            // Playing pairs
            sections.home.forEach((pair, i) => {{
                if (pair.anchor && pair.gunner) {{
                    const pairCvs = ((pair.anchor.cvs || 0) + (pair.gunner.cvs || 0)).toFixed(2);
                    const spread = Math.abs(pair.anchor.hi - pair.gunner.hi).toFixed(1);
                    csv += `${{pairNum++}},HOME,PLAY,${{pairCvs}},${{pair.anchor.name}},${{pair.anchor.hi}},${{pair.anchor.cvs || ''}},${{pair.anchor.commitment}},${{pair.gunner.name}},${{pair.gunner.hi}},${{pair.gunner.cvs || ''}},${{pair.gunner.commitment}},${{spread}}\\n`;
                }}
            }});

            sections.away.forEach((pair, i) => {{
                if (pair.anchor && pair.gunner) {{
                    const pairCvs = ((pair.anchor.cvs || 0) + (pair.gunner.cvs || 0)).toFixed(2);
                    const spread = Math.abs(pair.anchor.hi - pair.gunner.hi).toFixed(1);
                    csv += `${{pairNum++}},AWAY,PLAY,${{pairCvs}},${{pair.anchor.name}},${{pair.anchor.hi}},${{pair.anchor.cvs || ''}},${{pair.anchor.commitment}},${{pair.gunner.name}},${{pair.gunner.hi}},${{pair.gunner.cvs || ''}},${{pair.gunner.commitment}},${{spread}}\\n`;
                }}
            }});

            // Reserve pairs
            const reserves = [
                {{ section: sections.homeReserve[0], loc: 'HOME' }},
                {{ section: sections.awayReserve[0], loc: 'AWAY' }},
                {{ section: sections.generalReserve1[0], loc: 'GENERAL' }},
                {{ section: sections.generalReserve2[0], loc: 'GENERAL' }}
            ];

            reserves.forEach((r) => {{
                const pair = r.section;
                if (pair.anchor && pair.gunner) {{
                    const pairCvs = ((pair.anchor.cvs || 0) + (pair.gunner.cvs || 0)).toFixed(2);
                    const spread = Math.abs(pair.anchor.hi - pair.gunner.hi).toFixed(1);
                    csv += `${{pairNum++}},${{r.loc}},RESERVE,${{pairCvs}},${{pair.anchor.name}},${{pair.anchor.hi}},${{pair.anchor.cvs || ''}},${{pair.anchor.commitment}},${{pair.gunner.name}},${{pair.gunner.hi}},${{pair.gunner.cvs || ''}},${{pair.gunner.commitment}},${{spread}}\\n`;
                }}
            }});

            document.getElementById('exportText').value = csv;
            document.getElementById('exportArea').classList.add('visible');

            // Also download
            const blob = new Blob([csv], {{ type: 'text/csv' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'pairings_manual.csv';
            a.click();
        }}

        // Start
        init();
    </script>
</body>
</html>'''

    output_file = 'outputs/pairing_builder.html'
    with open(output_file, 'w') as f:
        f.write(html_content)

    print(f"\nPairing UI generated: {output_file}")
    print(f"Open in your browser to drag and drop players into pairs!")
    print(f"\nPlayers loaded: {len(all_players)}")
    print(f"  - Committed: {len(committed)}")
    print(f"  - Monthly: {len(monthly)}")
    print(f"  - TBC: {len(tbc)}")


if __name__ == "__main__":
    generate_pairing_ui()
