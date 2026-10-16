"""Controls for batched source selection and keeping API credentials out of files."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
import httpx
import collect_panel as collector


def response_fixture():
    rows=[]
    for reporter in [392,410]:
        for cmd,multiplier in [(854231,1),(854232,3)]:
            for partner,value in [(0,1000),(156,600),(344,400)]:
                rows.append(dict(reporterCode=reporter,period=202001,cmdCode=cmd,
                    partnerCode=partner,primaryValue=value*multiplier,classificationCode='H5',
                    flowCode='X',freqCode='M',partner2Code=0,customsCode='C00',motCode=0))
    return {'data':rows}


class NoDelay:
    def is_set(self):return False
    blocked=None
    def __init__(self):self.blocked=self
    def acquire(self):pass
    def completed(self):pass


class SourceControls(unittest.TestCase):
    def test_multi_product_source_is_selected_without_double_counting_or_secret_storage(self):
        secret='SYNTHETIC_TEST_KEY_DO_NOT_USE'
        fixture=response_fixture()
        class Client:
            def get(self,url):
                self_url=url
                assert secret in self_url
                return httpx.Response(200,json=fixture,request=httpx.Request('GET',url))
        tasks=[('M',r,202001,c) for r in [392,410] for c in [854231,854232]]
        with tempfile.TemporaryDirectory(prefix='comtrade_source_control_') as directory:
            with patch.object(collector,'CACHE',Path(directory)):
                results=collector.retrieve_group(tasks,NoDelay(),Client(),secret)
                self.assertEqual(len(results),4)
                self.assertTrue(all(r['check']['status']=='ok' and r['check']['rows']==3 for r in results))
                self.assertEqual({(r['reporter'],r['cmdCode']) for r in results},
                                 {(r,c) for r in [392,410] for c in [854231,854232]})
                for task in tasks:
                    cached=collector.read_cached(task)
                    self.assertEqual(cached['check']['status'],'ok')
                    self.assertEqual(cached['cmdCode'],task[3])
                    self.assertEqual(cached['check']['world_usd'],1000 if task[3]==854231 else 3000)
                for path in Path(directory).glob('*.meta.json'):
                    self.assertNotIn(secret,path.read_text())
                self.assertNotIn(secret,(Path(directory)/'request_attempts.jsonl').read_text())

    def test_error_redaction_handles_raw_and_url_encoded_credentials(self):
        secret='TEST/NOT+A+REAL+KEY'
        value=f'HTTP error at ?subscription-key={secret}'
        self.assertNotIn(secret,collector.redact(value,secret))
        encoded=collector.urllib.parse.quote(secret,safe='')
        self.assertNotIn(encoded,collector.redact('HTTP error '+encoded,secret))

    def test_unrequested_commodity_is_rejected(self):
        result=collector.validate(response_fixture(),'M',392,202001,854231,
                                  allowed_reporters=[392,410],allowed_cmds=[854231],max_records=100000)
        self.assertEqual(result['status'],'invalid')
        self.assertIn('unexpected_product_or_period_in_response',result['issues'])


if __name__=='__main__':unittest.main()
