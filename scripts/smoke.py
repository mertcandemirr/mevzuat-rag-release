"""Run five known questions through the frontend reverse proxy and check citations."""
import argparse
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

QUESTIONS = (
    ('KVKK 11. madde kapsamında hangi haklara sahibim?', '6698:normal:11'),
    ('Kişisel veri nedir?', '6698:normal:3:1:d'),
    ('Ev sahibi en fazla ne kadar depozito isteyebilir?', '6098:normal:342'),
    ('Kiracı sözleşme bitmeden evi boşaltırsa ne olur?', '6098:normal:325'),
    ('Fazla mesai ücreti nasıl hesaplanır?', '4857:normal:41'),
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8080')
    url = parser.parse_args().url.rstrip('/')
    path = Path(__file__).resolve().parents[1] / 'data/kanunlar/chunks.json'
    catalog = {r['document_id']: r['text'] for r in json.loads(path.read_text())}
    passed = 0
    for question, target in QUESTIONS:
        payload = json.dumps({'question': question}).encode()
        request = Request(url + '/api/chat', data=payload, headers={'Content-Type':'application/json'})
        with urlopen(request, timeout=150) as response:
            result = json.load(response)
        sent = set(result['trace'].get('llm_sent_source_ids', []))
        refs = result['sources']
        valid = all(s['id'] in sent and catalog.get(s['id']) == s['text'] for s in refs)
        cited = any(s['id'] == target or s['id'].startswith(target + ':') for s in refs)
        ok = bool(result['answer']) and valid and cited
        print('GEÇTİ' if ok else 'KALDI', question, [s['id'] for s in refs])
        passed += int(ok)
    print(f'{passed}/{len(QUESTIONS)} doğru kaynak')
    return int(passed != len(QUESTIONS))

if __name__ == '__main__':
    sys.exit(main())
