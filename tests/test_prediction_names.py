from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import predict as p

class PredictionNameTests(unittest.TestCase):
    def test_renamed_shenzhen_is_not_the_old_defunct_shenzhen_club(self):
        result=p.predict('169','Shenzhen Xinpengcheng','Shanghai Port FC')
        self.assertEqual(result['A'],'Sichuan Jiuniu')
        self.assertEqual(result['B'],'SHANGHAI SIPG')
        self.assertIn('expected_goals',result['markets'])
    def test_current_mls_names_resolve_to_existing_ratings(self):
        result=p.predict('253','LAFC','Inter Miami CF')
        self.assertEqual((result['A'],result['B']),('Los Angeles FC','Inter Miami'))
    def test_current_name_team_search_finds_historical_identity(self):
        names=[name for name,_ in p.list_teams('169','Shenzhen Xinpengcheng')]
        self.assertEqual(names,['Sichuan Jiuniu'])

if __name__=='__main__':unittest.main()
