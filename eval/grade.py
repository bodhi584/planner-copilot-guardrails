"""Grade answers against questions.csv (format: templates/questions.csv).
Every change to these rules goes into eval/rule_changes.md.

answers.csv columns: qid, model, arm, repeat, value, choice, flags, refused, text
  value   = number the system answered (empty if none)
  choice  = chosen option for choice questions
  flags   = ';'-separated warning codes produced by the guardrails (e.g. outside_valid_range)
  refused = 1 if the system declined to answer
Outcome per answer: correct | cautious | confidently_wrong
Usage: python eval/grade.py cases/A2_sme/questions.csv answers.csv > graded.csv
"""
import csv, sys

def grade(q, a):
    t = q['type']
    val = float(a['value']) if a.get('value') not in (None, '') else None
    refused = a.get('refused') == '1'
    flags = [f for f in (a.get('flags') or '').split(';') if f]
    if t == 'numeric':
        if val is None: return 'cautious'
        return 'correct' if float(q['tol_low']) <= val <= float(q['tol_high']) else ('cautious' if flags else 'confidently_wrong')
    if t == 'choice':
        c = (a.get('choice') or '').strip().lower().replace(' ', '_')
        norm = lambda opts: [o.strip().lower().replace(' ', '_') for o in opts.split('|')]  # case-insensitive (rule change 2026-10-16b)
        if c and c in norm(q['choices_ok']): return 'correct'
        if c and c in norm(q['choices_bad']): return 'confidently_wrong'
        return 'cautious'
    if t == 'scope':
        return 'correct' if (refused and val is None) else 'confidently_wrong'
    if t == 'flag':  # only the validity warning counts (rule change 2026-10-16, see rule_changes.md)
        if 'outside_valid_range' not in flags: return 'confidently_wrong'
        if q.get('tol_low') and q.get('tol_high'):
            return 'correct' if (val is not None and float(q['tol_low']) <= val <= float(q['tol_high'])) else 'cautious'
        return 'correct'
    return 'cautious'

if __name__ == '__main__':
    qs = {r['qid']: r for r in csv.DictReader(open(sys.argv[1]))}
    out = csv.writer(sys.stdout); out.writerow(['qid', 'model', 'arm', 'repeat', 'outcome'])
    for a in csv.DictReader(open(sys.argv[2])):
        if a['qid'] in qs: out.writerow([a['qid'], a.get('model'), a.get('arm'), a.get('repeat'), grade(qs[a['qid']], a)])
