"""
PL Data Validator
Run: python3 validate.py
Checks data integrity and quality for teams.json and players_details.json
"""

import json, os, sys

# Fix Windows console encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
ERRORS = []
WARNINGS = []

def err(msg):
    ERRORS.append(msg)
    print(f"  [ERROR] {msg}")

def warn(msg):
    WARNINGS.append(msg)
    print(f"  [WARN]  {msg}")

def ok(msg):
    print(f"  [OK]    {msg}")

# Load data
teams = players = None

try:
    with open(os.path.join(DATA_DIR, 'teams.json'), encoding='utf-8') as f:
        teams = json.load(f)
except Exception as e:
    err(f"Cannot load teams.json: {e}")

try:
    with open(os.path.join(DATA_DIR, 'players_details.json'), encoding='utf-8') as f:
        players = json.load(f)
except Exception as e:
    warn(f"Cannot load players_details.json: {e}")

checkpoint = None
try:
    with open(os.path.join(DATA_DIR, '_checkpoint.json'), encoding='utf-8') as f:
        checkpoint = json.load(f)
except:
    pass

print("\n========== TEAMS VALIDATION ==========\n")

if teams:
    # 1. Team count
    if len(teams) == 20:
        ok(f"20 teams loaded")
    else:
        err(f"Expected 20 teams, got {len(teams)}")

    # 2. Each team has players
    empty_teams = [t['name'] for t in teams if not t.get('players')]
    if empty_teams:
        err(f"Teams with empty squad: {empty_teams}")
    else:
        ok("All teams have squad data")

    # 3. Check for recommended player contamination
    total_players = 0
    for t in teams:
        total_players += len(t.get('players', []))

    print(f"\n  Total players across all teams: {total_players}")

    # 4. Per-team check
    for t in teams:
        squad = t.get('players', [])
        issues = []
        for p in squad:
            # Check position is clean
            pos = p.get('position', '')
            name = p.get('name', '')
            if not pos:
                issues.append(f"{name} has no position")
            elif name and pos and name.lower() in pos.lower():
                issues.append(f"{name}: position '{pos}' contains name (contaminated)")
            # Check nationality
            if not p.get('nationality'):
                issues.append(f"{name} has no nationality")
            # Check ID format
            if not p.get('id') or not p['id'].isdigit():
                issues.append(f"{name} has invalid id")
        if issues:
            for issue in issues[:3]:
                err(f"[{t['name']}] {issue}")
            if len(issues) > 3:
                warn(f"[{t['name']}] +{len(issues)-3} more issues")
        else:
            ok(f"{t['name']:15s} {len(squad):2d} players — all clean")

    # 5. Duplicate player IDs
    all_pids = {}
    for t in teams:
        for p in t.get('players', []):
            pid = p.get('id')
            if pid:
                all_pids.setdefault(pid, []).append(t['name'])
    dups = {pid: teams for pid, teams in all_pids.items() if len(teams) > 1}
    if dups:
        for pid, teams in dups.items():
            err(f"Player {pid} appears in multiple teams: {teams}")
    else:
        ok("No duplicate player IDs across teams")

    # 6. Player counts per team
    print("\n  --- Team sizes ---")
    counts = sorted([(t['name'], len(t.get('players', []))) for t in teams], key=lambda x: x[1])
    for name, cnt in counts:
        print(f"    {name:15s} {cnt}")
    print(f"    {'TOTAL':15s} {total_players}")

    avg = total_players / len(teams)
    for name, cnt in counts:
        if cnt < 18:
            warn(f"{name} only has {cnt} players (small squad)")
        elif cnt < 15:
            err(f"{name} only has {cnt} players (very small)")

print("\n========== PLAYER DETAILS VALIDATION ==========\n")

if players:
    total = len(players)
    ok(f"{total} player records loaded")

    # Field completeness
    fields_of_interest = ['birth_date', 'birth_place', 'height', 'foot', 'agent', 'contract_expiry', 'joined', 'market_value']
    print("\n  --- Detail field coverage ---")
    for field in fields_of_interest:
        filled = sum(1 for p in players if p.get(field))
        pct = filled * 100 / total if total else 0
        if pct < 50 and filled < total:  # Allow partial coverage during crawl
            if filled == 0:
                err(f"{field}: 0/{total} (0%) — extraction failed!")
            else:
                warn(f"{field}: {filled}/{total} ({pct:.0f}%)")
        else:
            ok(f"{field}: {filled}/{total} ({pct:.0f}%)")

    # Duplicate players
    seen = {}
    for p in players:
        pid = p.get('id')
        if pid:
            seen.setdefault(pid, []).append(p.get('name', '?'))
    dups = {pid: names for pid, names in seen.items() if len(names) > 1}
    if dups:
        err(f"Duplicate player IDs in details: {len(dups)} players appear multiple times")
        for pid, names in list(dups.items())[:5]:
            err(f"  ID {pid}: {', '.join(set(names))}")

    # Detail errors
    detail_errors = sum(1 for p in players if p.get('detail_error'))
    if detail_errors:
        warn(f"{detail_errors}/{total} players had fetch errors")
    else:
        ok("No fetch errors")

    # Missing market values
    no_mv = [p['name'] for p in players if not p.get('market_value') or p.get('market_value') == '-']
    if no_mv:
        warn(f"{len(no_mv)} players without market value (e.g. {', '.join(no_mv[:5])})")
    else:
        ok("All players have market values")

else:
    warn("Skipping detail validation (no players_details.json)")

print("\n========== CRAWL STATUS ==========\n")
if checkpoint:
    step = checkpoint.get('step', 'unknown')
    ok(f"Checkpoint step: {step}")
    if 'progress' in checkpoint:
        print(f"  Progress: {checkpoint['progress']}")
    if 'done_details' in checkpoint:
        print(f"  Details fetched: {len(checkpoint['done_details'])} players")
    if step != 'done':
        warn("Crawl is not yet complete")
    else:
        ok("Crawl completed!")
else:
    warn("No checkpoint file")

print(f"\n========== SUMMARY ==========")
print(f"  ERRORS:   {len(ERRORS)}")
print(f"  WARNINGS: {len(WARNINGS)}")
if ERRORS:
    print(f"\n  ❌ There are {len(ERRORS)} errors that need fixing!")
    sys.exit(1)
elif WARNINGS:
    print(f"\n  ⚠️  {len(WARNINGS)} warnings (review recommended)")
    sys.exit(0)
else:
    print(f"\n  ✅ All checks passed!")
    sys.exit(0)
