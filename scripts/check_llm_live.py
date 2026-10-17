"""Explicit, paid opt-in integration check; credentials are read only into memory."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from desktop.backend import Backend
from mystery.llm import list_models, ping_model, make_config, interpret_chart_stream


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--settings', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    provider = json.loads(args.settings.read_text(encoding='utf-8'))['providers']['siliconflow']
    config = {k: provider[k] for k in ('api_base', 'api_key')}
    config.update(model=provider['models']['full'], lite_model=provider['models']['lite'])
    report = {'provider': 'SiliconFlow', 'model': config['model'], 'lite_model': config['lite_model'], 'checks': {}}

    def save(name, result):
        report['checks'][name] = result
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(name, json.dumps(result, ensure_ascii=False), flush=True)

    def safe_error(error):
        return str(error).replace(config['api_key'], '[hidden]')[:500]

    try:
        models = list_models(config['api_base'], config['api_key'])
        save('models', {'ok': bool(models), 'count': len(models), 'full_listed': config['model'] in models, 'lite_listed': config['lite_model'] in models})
    except Exception as error:
        save('models', {'ok': False, 'error': safe_error(error)})
    for kind in ('model', 'lite_model'):
        try:
            reply = ping_model(config['api_base'], config['api_key'], config[kind], timeout=120)
            save('ping_' + kind, {'ok': bool(reply), 'characters': len(reply)})
        except Exception as error:
            save('ping_' + kind, {'ok': False, 'error': safe_error(error)})

    def check(module):
        with tempfile.TemporaryDirectory(prefix='mystery-llm-') as folder:
            backend = Backend(Path(folder))
            p = {'module': module, 'datetime': '2000-08-16T04:00', 'longitude': 116.41, 'latitude': 39.90,
                 'tz_name': 'Asia/Shanghai', 'first': 34, 'second': 43, 'question': '近期如何安排学习？'}
            if module in ('tarot', 'lenormand'):
                p.update(backend.shuffle(p))
            record = backend.calculate(p)
            reference = backend.calculate(p if module not in ('tarot', 'lenormand') else {**p, **backend.shuffle(p)})
            facts = json.dumps(record['result'], sort_keys=True)

            def request(extra):
                started = time.monotonic()
                job = backend.start_ai({**config, 'id': record['id'], **extra})
                cursor = 0
                chars = 0
                errors = []
                usage = None
                while True:
                    poll = backend.poll({'job': job['job'], 'cursor': cursor})
                    cursor = poll['cursor']
                    for event in poll['events']:
                        if event['type'] == 'delta': chars += len(event.get('text', ''))
                        if event['type'] == 'error': errors.append(event)
                        if event['type'] == 'usage': usage = event
                    if poll['done']: break
                    if time.monotonic() - started > 480: raise TimeoutError('Job exceeded 480 seconds')
                    time.sleep(.2)
                saved = backend.get(record['id'])
                return {'ok': chars > 0 and not errors and not saved.get('ai_incomplete'), 'characters': chars,
                        'seconds': round(time.monotonic() - started, 1), 'errors': errors, 'usage': usage,
                        'facts_unchanged': json.dumps(saved['result'], sort_keys=True) == facts}

            results = {'interpretation': request({})}
            print(module + ' interpretation complete', flush=True)
            if results['interpretation']['ok']:
                results['followup_with_reference'] = request({'question': '对照两份记录，只用三句话说明相同的结构事实，不要重排。', 'refs': [reference['id']]})
                results['history_persisted'] = len(backend.get(record['id'])['history']) == 2
            results['ok'] = results['interpretation']['ok'] and results.get('followup_with_reference', {}).get('ok', False) and results.get('history_persisted', False)
            return results

    with ThreadPoolExecutor(max_workers=3) as pool:
        pending = {pool.submit(check, module): module for module in ('bazi', 'astro', 'ziwei', 'jyotish', 'liuyao', 'meihua', 'tarot', 'lenormand')}
        for future in as_completed(pending):
            try: save(pending[future], future.result())
            except Exception as error: save(pending[future], {'ok': False, 'error': safe_error(error)})
    try:
        from mystery.bazi import calculate_bazi
        fallback_config = make_config(config['api_base'], config['api_key'],
                                      'mystery-intentional-invalid-model-for-fallback',
                                      lite_model=config['lite_model'], fallback=True, retry=0)
        events = list(interpret_chart_stream(calculate_bazi(2000, 8, 16, 4, 0, use_true_solar=False), fallback_config))
        save('fallback', {'ok': any(e['type'] == 'notice' for e in events)
                         and any(e['type'] == 'delta' for e in events)
                         and not any(e['type'] == 'error' for e in events),
                         'characters': sum(len(e.get('text', '')) for e in events if e['type'] == 'delta'),
                         'preview_usage': next((e for e in events if e['type'] == 'usage'), None)})
    except Exception as error:
        save('fallback', {'ok': False, 'error': safe_error(error)})
    report['ok'] = all(item['ok'] for item in report['checks'].values())
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
