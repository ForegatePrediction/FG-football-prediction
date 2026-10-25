import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import refresh as r

class RefreshTests(unittest.TestCase):
    def event(self, status='STATUS_FULL_TIME', date='2026-10-24T18:00Z'):
        return {'id':'42','uid':'s:600~l:700~e:42','date':date,
                'status':{'type':{'name':status,'completed':True}},
                'competitions':[{'competitors':[
                    {'homeAway':'home','team':{'id':'1','displayName':'Tottenham Hotspur'},'score':'2'},
                    {'homeAway':'away','team':{'id':'2','displayName':'Arsenal'},'score':'1'}]}]}
    def test_regulation_only_and_league_identity(self):
        self.assertEqual(r.parse_event(self.event(),{'700':'39'})['code'],'39')
        self.assertIsNone(r.parse_event(self.event('STATUS_FINAL_PEN'),{'700':'39'}))
        self.assertIsNone(r.parse_event(self.event(),{'775':'2'}))
    def test_fetch_utc_day_and_duplicate_protection(self):
        events=[self.event(),self.event(date='2026-10-25T01:00Z')]
        with patch.object(r,'get_json',return_value={'events':events}) as get:
            result=r.fetch_matches(['2026-10-24'],{'39':{'id':'700'}})
        self.assertEqual(len(result),1)
        self.assertTrue(any('dates=20261023' in c.args[0] for c in get.call_args_list))
    def test_failed_request_cannot_be_empty_success(self):
        with patch.object(r.urllib.request,'urlopen',side_effect=OSError),patch.object(r.time,'sleep'):
            with self.assertRaises(RuntimeError):r.get_json('https://example.invalid')
    def test_womens_teams_are_separate_from_mens(self):
        with patch.object(r,'get_json',return_value={'events':[self.event()]}):
            rows=r.fetch_matches(['2026-10-24'],{'525':{'id':'700','women':True}})
        self.assertEqual(rows[0]['home'],'Tottenham Hotspur W')
        teams={'Tottenham':{},'Tottenham W':{}}
        self.assertEqual(r.team_name(rows[0]['home'],'99',teams,{},{}),'Tottenham W')
    def test_safe_names_do_not_merge_manchester_clubs(self):
        teams={'Manchester City':{},'Manchester United':{},'Tottenham':{}}
        identity={}
        self.assertEqual(r.team_name('Tottenham Hotspur','1',teams,identity,{}),'Tottenham')
        self.assertEqual(r.team_name('Manchester','2',teams,identity,{}),'Manchester')
    def test_provider_id_alias_preserves_existing_club_history(self):
        with patch.dict(r.TEAM_ALIASES,{'club-1':'Los Angeles FC'}):
            identity={'club-1':'LAFC'}
            self.assertEqual(r.team_name('LAFC','club-1',{'Los Angeles FC':{'gp':200}},identity,{}),'Los Angeles FC')
            self.assertEqual(identity['club-1'],'Los Angeles FC')
    def test_incremental_replay_and_same_day_late_game(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(r,'GAMES',Path(tmp)):
            snap={'teams':{'Tottenham':{},'Arsenal':{}},'last_date':'2026-10-23'}
            match=r.parse_event(self.event(),{'700':'39'})
            self.assertEqual(r.apply_matches('39',snap,{},[match]),1)
            path=Path(tmp)/'39/ratings.json';out=json.loads(path.read_text())
            self.assertEqual(out['teams']['Tottenham']['gp'],1)
            self.assertEqual(r.apply_matches('39',out,{},[match]),0)
            other={**match,'id':'43'}
            self.assertEqual(r.apply_matches('39',out,{},[match,other]),1)
    def test_backfill_never_skips_history(self):
        snaps={'a':{'last_date':'2026-03-31'},'b':{'last_date':'2026-06-20'}}
        days=r.date_window(snaps,{},31,dt.date(2026,10,24))
        self.assertEqual((days[0],days[-1]),('2026-04-01','2026-05-01'))
        days=r.date_window(snaps,{'checked_through':'2026-10-23'},0,dt.date(2026,10,24))
        self.assertEqual(days,['2026-10-23','2026-10-24'])

if __name__=='__main__':unittest.main()
