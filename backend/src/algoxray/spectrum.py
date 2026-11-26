"""Bounded spectrum comparison. Scores are suspicion ranks, never causal probabilities."""
from collections import Counter
from math import sqrt

def coverage(events):
    return sorted({e["line"] for e in events if e["kind"]=="line"})

def rank_spectrum(samples, witness_events):
    passing = [s for s in samples if s["outcome"]=="pass"]
    failing = [s for s in samples if s["outcome"]=="fail"]
    if not passing or not failing:
        return []
    p=Counter(line for s in passing for line in s["lines"])
    f=Counter(line for s in failing for line in s["lines"])
    events={}
    for e in witness_events:
        if e["kind"]=="line": events.setdefault(e["line"],e["event_id"])
    rows=[]
    for line, count in f.items():
        if line not in events: continue
        score=count/sqrt(len(failing)*(count+p[line]))
        rows.append({"line":line,"event_id":events[line],"failed_covered":count,
                     "passed_covered":p[line],"failed_total":len(failing),"passed_total":len(passing),
                     "score":round(score,6),"basis":"ochiai_suspicion","causal_fault_proven":False})
    return sorted(rows,key=lambda r:(-r["score"],r["line"]))[:10]
