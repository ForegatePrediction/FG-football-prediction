#!/usr/bin/env python3
"""Free ESPN finished results, incremental league and shared-pool ratings.
Only completed UTC days are checkpointed. Fetch/validate the whole batch before
writing; a failed request cannot advance the cursor. No API key or paid endpoint.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import gzip
import json
import os
from pathlib import Path
import re
import sys
import time
import unicodedata
import urllib.request
from core.ratings import PoissonRatings

ROOT = Path(__file__).resolve().parent
GAMES = ROOT / 'games'
BASE = 'https://site.api.espn.com/apis/site/v2/sports/soccer'
TEAM_ALIASES = json.loads((ROOT/'team-aliases.json').read_text())
# Explicit name equivalents only; never use fuzzy prediction matching for training.
ALIASES = {
    'Tottenham Hotspur': 'Tottenham', 'Newcastle United': 'Newcastle',
    'Wolverhampton Wanderers': 'Wolves', 'Brighton & Hove Albion': 'Brighton',
    'West Ham United': 'West Ham', 'Leicester City': 'Leicester',
    'Leeds United': 'Leeds', 'Ipswich Town': 'Ipswich', 'Luton Town': 'Luton',
    'Sheffield United': 'Sheffield Utd', 'West Bromwich Albion': 'West Brom',
    'Queens Park Rangers': 'QPR', 'Norwich City': 'Norwich',
    'Bayern Munich': 'Bayern Munich', 'Bayer Leverkusen': 'Bayer Leverkusen',
    'Mainz': 'FSV Mainz 05', 'TSG Hoffenheim': '1899 Hoffenheim',
    'Borussia Mönchengladbach': 'Borussia Monchengladbach',
    'Paris Saint-Germain': 'Paris Saint Germain', 'Brest': 'Stade Brestois 29',
    'Internazionale': 'Inter', 'AS Roma': 'AS Roma', 'Athletic Club': 'Athletic Club',
    'AFC Bournemouth': 'Bournemouth', 'Coventry City': 'Coventry',
    'Deportivo': 'Deportivo La Coruna', '1. FC Union Berlin': 'Union Berlin',
    'FC Cologne': '1. FC Köln', 'Hamburg SV': 'Hamburger SV', 'Schalke 04': 'FC Schalke 04',
    'AJ Auxerre': 'Auxerre', 'AS Monaco': 'Monaco', 'Le Havre AC': 'Le Havre',
    'Stade Rennais': 'Rennes', 'Troyes': 'Estac Troyes',
    'United States': 'USA', 'Korea Republic': 'South Korea',
    'China': 'China PR', 'Türkiye': 'Turkey', 'Czechia': 'Czech Republic',
}


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def get_json(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=35) as response:
                body = response.read()
            if body[:2] == b'\x1f\x8b':
                body = gzip.decompress(body)
            result = json.loads(body)
            if not isinstance(result, dict) or not isinstance(result.get('events'), list):
                raise ValueError('Missing events list')
            if len(result['events']) >= 1000:
                raise ValueError('Scoreboard limit reached; refuse truncated results')
            return result
        except Exception:
            if attempt == 2:
                raise RuntimeError(f'ESPN scoreboard request failed: {url}') from None
            time.sleep(1 + attempt)


def parse_event(event, source_ids):
    league = re.search(r'(?:^|~)l:(\d+)(?:~|$)', event.get('uid', ''))
    if not league or league[1] not in source_ids:
        return None
    # FT = 90 minutes. Exclude AET/penalty results so goals remain comparable.
    status = event['status']['type']
    if not status.get('completed') or status.get('name') != 'STATUS_FULL_TIME':
        return None
    sides = {c['homeAway']: c for c in event['competitions'][0]['competitors']}
    home, away = sides['home'], sides['away']
    return {'id': str(event['id']), 'code': source_ids[league[1]],
            'date': event['date'][:10], 'kickoff': event['date'],
            'home': home['team']['displayName'], 'away': away['team']['displayName'],
            'home_id': str(home['team']['id']), 'away_id': str(away['team']['id']),
            'hg': int(home['score']), 'ag': int(away['score'])}


def date_window(snapshots, state, max_days, end=None):
    end = end or (dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1))
    if state.get('checked_through'):
        # Replay the boundary for delayed FT corrections; IDs prevent duplicates.
        start = dt.date.fromisoformat(state['checked_through'])
    else:
        start = min(dt.date.fromisoformat(s['last_date']) for s in snapshots.values()) + dt.timedelta(days=1)
    stop = min(end, start + dt.timedelta(days=max_days - 1)) if max_days else end
    return [(start + dt.timedelta(days=n)).isoformat() for n in range(max(0, (stop-start).days+1))]


def fetch_matches(dates, sources):
    if not dates:
        return []
    ids = {value['id']: code for code, value in sources.items()}
    # ESPN local days can contain matches on the next UTC day.
    days = [(dt.date.fromisoformat(dates[0])-dt.timedelta(days=1)).isoformat()] + dates
    def fetch(day):
        result = get_json(f"{BASE}/all/scoreboard?dates={day.replace('-', '')}&limit=1000")
        print(f"[fetch] {day}: {len(result['events'])} events", flush=True)
        return result['events']
    wanted, seen, matches = set(dates), set(), []
    with ThreadPoolExecutor(max_workers=4) as executor:
        for events in executor.map(fetch, days):
            for event in events:
                match = parse_event(event, ids)
                if match and match['date'] in wanted and match['id'] not in seen:
                    if sources[match['code']].get('women'):
                        match['home'] += ' W'
                        match['away'] += ' W'
                        match['home_id'] = 'w:' + match['home_id']
                        match['away_id'] = 'w:' + match['away_id']
                    matches.append(match)
                    seen.add(match['id'])
    return sorted(matches, key=lambda m: (m['kickoff'], m['id']))


def normalize(name):
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', name)


def team_name(name, identifier, teams, identity, index):
    if identifier in TEAM_ALIASES:
        identity[identifier] = TEAM_ALIASES[identifier]
        return identity[identifier]
    if identifier in identity:
        return identity[identifier]
    preferred = (ALIASES.get(name[:-2], name[:-2]) + ' W') if name.endswith(' W') else ALIASES.get(name, name)
    if preferred in teams:
        canonical = preferred
    elif name in teams:
        canonical = name
    else:
        candidates = index.get(normalize(preferred), [])
        # Ambiguous historical spellings are kept separate for human review.
        canonical = candidates[0] if len(candidates) == 1 else preferred
    identity[identifier] = canonical
    return canonical


def apply_matches(code, snapshot, config, matches):
    last = snapshot.get('last_date', '')
    seen = set(snapshot.get('applied_on_last_date', []))
    has_ledger = 'applied_on_last_date' in snapshot
    fresh = [m for m in matches if m['date'] > last or
             (m['date'] == last and has_ledger and m['id'] not in seen)]
    if not fresh:
        return 0
    rating = PoissonRatings.from_snapshot(snapshot, lr=config.get('lr', .03))
    identity = dict(snapshot.get('espn_team_names', {}))
    index = {}
    for name in snapshot['teams']:
        index.setdefault(normalize(name), []).append(name)
    for match in fresh:
        h = team_name(match['home'], match['home_id'], snapshot['teams'], identity, index)
        a = team_name(match['away'], match['away_id'], snapshot['teams'], identity, index)
        rating.update(h, a, match['hg'], match['ag'])
    latest = max(m['date'] for m in fresh)
    value = {**snapshot, **rating.snapshot(), 'last_date': latest,
             'updated_from': snapshot.get('updated_from', 0) + len(fresh),
             'espn_team_names': identity,
             'applied_on_last_date': sorted((seen if latest == last else set()) |
                                           {m['id'] for m in fresh if m['date'] == latest})}
    write_json(GAMES / code / 'ratings.json', value)
    print(f"[apply] {code}: +{len(fresh)}, last_match={latest}")
    return len(fresh)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-days', type=int, default=31, help='0 = complete backfill')
    args = parser.parse_args()
    if args.max_days < 0:
        parser.error('max-days must be >= 0')
    sources = json.loads((ROOT/'free-sources.json').read_text())
    configs = {p.parent.name: json.loads(p.read_text()) for p in GAMES.glob('*/config.json')}
    snapshots = {code: json.loads((GAMES/code/'ratings.json').read_text())
                 for code in set(sources) | {'_clubpool', '_natpool'}
                 if (GAMES/code/'ratings.json').exists()}
    state_path = ROOT/'refresh-state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    for code in sources:
        target = configs[code].get('pool_ref', code)
        if target not in snapshots:
            raise RuntimeError(f'Missing rating pool for {code}: {target}')
    dates = date_window(snapshots, state, args.max_days)
    if not dates:
        print('No completed UTC day pending')
        return
    print(f"Checking {dates[0]} through {dates[-1]} ({len(dates)} days)", flush=True)
    matches = fetch_matches(dates, sources)  # All requests complete before any write.
    grouped = {code: [] for code in snapshots}
    coverage = dict(state.get('competitions', {}))
    for match in matches:
        code = match['code']
        if code in grouped:
            grouped[code].append(match)
        # Women's national teams have a separate league snapshot, not the men's pool.
        if code != '880':
            pool = configs[code].get('pool_ref', '_clubpool')
            grouped[pool].append(match)
        previous = coverage.get(code, {})
        coverage[code] = {**previous, 'latest_source_match': max(previous.get('latest_source_match', ''), match['date'])}
    total = 0
    for code, snapshot in snapshots.items():
        total += apply_matches(code, snapshot, configs.get(code, {}), grouped[code])
    for code, source in sources.items():
        pool = configs[code].get('pool_ref', code)
        current = json.loads((GAMES/pool/'ratings.json').read_text())
        coverage[code] = {**coverage.get(code, {}), 'name': configs[code]['name'],
                          'source': 'espn', 'slug': source['slug'], 'checked_through': dates[-1],
                          'last_rating_match': current.get('last_date'),
                          'source_matches_in_batch': sum(m['code'] == code for m in matches)}
    write_json(state_path, {'checked_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                           'checked_through': dates[-1], 'competitions': coverage})
    print(f'Completed: {len(matches)} distinct FT matches, {total} pool/league updates')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as f:
            f.write(f'Free ESPN: {dates[0]}–{dates[-1]}, {len(matches)} FT matches.\n\n')
            f.write('|Competition|Latest source FT|Checked through|\n|---|---|---|\n')
            for code, item in coverage.items():
                f.write(f"|{code}: {item['name']}|{item.get('latest_source_match', 'No FT in checked window')}|{dates[-1]}|\n")


if __name__ == '__main__':
    main()
