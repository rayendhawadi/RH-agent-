import sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from app.core.database import SessionLocal
from app.services.reporting.aggregates import (
    sla_parsing_scoring, stage_timings, score_distribution,
    needs_attention_queue, cost_per_hire
)
from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.score import Score
from app.models.llm_usage import LLMUsage

errors = []

def check(label, ok, detail=''):
    s = 'OK  ' if ok else 'FAIL'
    msg = '  [' + s + '] ' + label
    if detail:
        msg += ' -- ' + detail
    print(msg)
    if not ok:
        errors.append(label)

db = SessionLocal()
try:
    print('\n=== VALIDATION REPORTING A9 ===\n')

    # 1. Donnees de base
    total_apps = db.query(Application).count()
    total_scores = db.query(Score).count()
    total_llm = db.query(LLMUsage).count()
    print('[1] Donnees de base')
    print('  Candidatures : ' + str(total_apps))
    print('  Scores       : ' + str(total_scores))
    print('  Appels LLM   : ' + str(total_llm))
    check('Au moins 1 candidature', total_apps > 0)

    # 2. SLA Parsing / Scoring
    print('\n[2] SLA Parsing / Scoring')
    sla = sla_parsing_scoring(db)
    p = sla['parsing']
    s = sla['scoring']
    print('  Parsing: avg=' + str(p['avg_min']) + 'min  p95=' + str(p['p95_min']) + 'min  N=' + str(p['n']))
    print('  Scoring: avg=' + str(s['avg_min']) + 'min  p95=' + str(s['p95_min']) + 'min  N=' + str(s['n']))
    check('Parsing N > 0 (fix created_at applique)', p['n'] > 0)
    check('Parsing avg >= 0', p['avg_min'] >= 0)
    check('Parsing p95 >= avg', p['p95_min'] >= p['avg_min'])
    if s['n'] > 0:
        check('Scoring avg >= 0', s['avg_min'] >= 0)
        check('Scoring p95 >= avg', s['p95_min'] >= s['avg_min'])
    else:
        print('  [WARN] Scoring N=0 -- aucun log PARSED->SCORED trouve')

    # 3. Stage Timings
    print('\n[3] Stage Timings (funnel)')
    timings = stage_timings(db)
    print('  ' + str(len(timings)) + ' transitions mesurees')
    for t in timings:
        print('  ' + t['stage'] + ': avg=' + str(t['avg_hours']) + 'h  N=' + str(t['n']))
    check('Au moins 1 transition funnel mesuree', len(timings) > 0)
    check('Toutes durees >= 0', all(t['avg_hours'] >= 0 for t in timings))

    # 4. Score Distribution
    print('\n[4] Distribution des scores')
    dist = score_distribution(db)
    total_in_buckets = sum(b['count'] for b in dist)
    print('  Total dans buckets : ' + str(total_in_buckets) + ' (attendu : ' + str(total_scores) + ')')
    for b in dist:
        print('  ' + b['range'] + ' pts : ' + str(b['count']) + ' candidats')
    check('Somme buckets == total scores', total_in_buckets == total_scores,
          'buckets=' + str(total_in_buckets) + ' scores=' + str(total_scores))
    check('Pas de bucket negatif', all(b['count'] >= 0 for b in dist))

    # 5. Needs Attention
    print('\n[5] Needs Attention')
    na = needs_attention_queue(db)
    print('  Total : ' + str(na['total']))
    if na['total'] > 0:
        print('  Raisons : ' + str(na['by_reason']))
        ages = [i['age_hours'] for i in na['oldest'] if i['age_hours'] is not None]
        check('Ages positifs', all(a >= 0 for a in ages))
        check('Trie par anciennete decroissante', ages == sorted(ages, reverse=True))
    else:
        print('  [INFO] Aucune candidature en NEEDS_ATTENTION')

    # 6. Cout par embauche
    print('\n[6] Cout par embauche (90 jours)')
    cost = cost_per_hire(db)
    print('  Tokens  : ' + str(cost['total_tokens']))
    print('  Cout USD: $' + str(cost['total_cost_usd_estimate']))
    print('  Embauche: ' + str(cost['hires']))
    if cost['hires'] > 0:
        print('  Tok/hire: ' + str(cost['tokens_per_hire']))
        print('  USD/hire: $' + str(cost['cost_usd_per_hire_estimate']))
    check('Cout >= 0', cost['total_cost_usd_estimate'] >= 0)
    expected_cost = round((cost['total_tokens'] / 1000) * 0.0002, 4)
    check('Formule cout = tokens/1000 * 0.0002',
          abs(cost['total_cost_usd_estimate'] - expected_cost) < 0.0001,
          'attendu=' + str(expected_cost) + ' obtenu=' + str(cost['total_cost_usd_estimate']))
    if cost['hires'] > 0:
        expected_tph = int(cost['total_tokens'] / cost['hires'])
        check('tokens_per_hire = total/hires',
              cost['tokens_per_hire'] == expected_tph,
              'attendu=' + str(expected_tph) + ' obtenu=' + str(cost['tokens_per_hire']))

    # Résumé
    print('\n' + '='*50)
    if errors:
        print('RESULTAT: ECHEC -- ' + str(len(errors)) + ' verification(s) echouee(s):')
        for e in errors:
            print('  - ' + e)
    else:
        print('RESULTAT: SUCCES -- Toutes les verifications sont passees !')
    print('='*50 + '\n')

finally:
    db.close()
