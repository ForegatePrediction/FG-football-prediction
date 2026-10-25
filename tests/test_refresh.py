from pathlib import Path
import sys
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import refresh
class RefreshTests(unittest.TestCase):
    def test_payment_error_inside_http_200_fails(self):
        response=Mock();response.json.return_value={'errors':{'plan':'expired'},'response':[]}
        with patch.object(refresh,'requests',Mock(get=Mock(return_value=response))):
            with self.assertRaises(RuntimeError):refresh._get('/fixtures')
    def test_http_error_fails(self):
        response=Mock();response.raise_for_status.side_effect=RuntimeError('403')
        with patch.object(refresh,'requests',Mock(get=Mock(return_value=response))):
            with self.assertRaises(RuntimeError):refresh._get('/fixtures')
    def test_paid_api_requires_explicit_opt_in(self):
        with patch.object(sys,'argv',['refresh.py']):
            with self.assertRaises(SystemExit):refresh.main()
if __name__=='__main__':unittest.main()
