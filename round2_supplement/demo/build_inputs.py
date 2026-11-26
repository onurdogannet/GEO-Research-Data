#!/usr/bin/env python3
"""Construct a disclosed, finite fictional fixture; never call a model or website."""
from pathlib import Path
import csv
import itertools
import json

ROOT = Path(__file__).resolve().parent

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)

def main():
    spec = json.loads((ROOT/'fixture_spec.json').read_text(encoding='utf-8'))
    inputs = ROOT/'inputs'
    (inputs/'responses').mkdir(parents=True, exist_ok=True)
    (inputs/'sources').mkdir(exist_ok=True)
    entities = {item['product_id']: item for item in spec['entities']}
    (inputs/'entities.json').write_text(json.dumps(spec['entities'], indent=2)+'\n', encoding='utf-8')
    source_index = []
    for entity, case in itertools.product(spec['entities'], range(4)):
        source_id = f"DOC_{entity['product_id']}_S{case}"
        path = f"sources/{source_id}.txt" if case != 3 else ''
        source_index.append({'source_id':source_id, 'document_path':path,
                             'availability':'available' if case != 3 else 'intentionally_unavailable',
                             'origin':'authored_fictional_document'})
        if case == 3:
            continue
        battery = entity['battery_hours'] + (5 if case == 2 else 0)
        warranty = f"{entity['warranty_years']} years" if case != 1 else 'Not stated'
        body = ("Fictional evidence document for the constructed demonstration.\n"
                "No external publisher or product is represented.\n"
                f"Document ID: {source_id}\n"
                f"Publisher type: {spec['source_types'][case]}\n"
                f"Product: {entity['name']}\n"
                f"Battery life: {battery} hours.\n"
                f"Warranty: {warranty}.\n")
        (inputs/path).write_text(body, encoding='utf-8')
    write_csv(inputs/'source_index.csv', source_index, list(source_index[0]))
    rows = []
    for q,w,c,s,r in itertools.product(range(2),range(2),range(2),range(2),range(2)):
        query = spec['queries'][q]
        scenario = ['X','Y'][c]
        pattern = (2*q+w+2*s+r)%4
        pids = spec['scenario_patterns'][scenario][pattern]
        names = [entities[pid]['alias' if w else 'name'] for pid in pids]
        strength = (q+2*w+s+r+c)%5
        case = (q+w+s+r+c)%4
        first = entities[pids[0]]
        source_id = f"DOC_{pids[0]}_S{case}"
        record_id = f"D_{query['query_id']}_W{w}_{scenario}_S{s}_R{r}"
        body = ["Constructed fictional shopping answer. No platform was queried.",
                "Options in display order:", *[f"- {name}" for name in names],
                f"Comparison: {names[0]} has {entities[pids[0]]['battery_hours']} hours of stated battery life, compared with {entities[pids[1]]['battery_hours']} hours for {names[1]}."]
        if pattern%2:
            body += [f"Prioritization: {names[-1]} has a comfort advantage for {query['need']} in this constructed example."]
        if strength == 1:
            body += [f"Advice: You could choose {names[-1]} first, followed by {names[0]}, if the listed features meet your needs."]
        elif strength == 2:
            body += [f"Advice: I recommend {names[-1]} first, followed by {names[0]}."]
        elif strength == 3:
            body += [f"Advice: I strongly recommend {names[-1]} first, followed by {names[0]}."]
        elif strength == 4:
            body += [f"Advice: Choose {names[-1]} first, followed by {names[0]}; {names[-1]} is clearly the best overall option for these needs."]
        if strength == 4 or (strength>=2 and q==0):
            body += [f"Overall choice: {names[-1]} is my single overall choice for these needs."]
        body += [f"Evidence-linked claim: {names[0]} has a battery life of {first['battery_hours']} hours and a warranty of {first['warranty_years']} years [{source_id}]."]
        response_path = f"responses/{record_id}.txt"
        (inputs/response_path).write_text('\n'.join(body)+'\n', encoding='utf-8')
        rows.append({'record_id':record_id,'query_id':query['query_id'],'wording':w,
                     'scenario':scenario,'snapshot':s,'replicate':r,
                     'prompt':query['wordings'][w],'response_path':response_path,
                     'origin':'new_authored_fictional_fixture'})
    write_csv(inputs/'record_index.csv', rows, list(rows[0]))
    print(f'Constructed {len(rows)} fictional answers and 12 fictional source documents; 4 source locators intentionally unavailable.')

if __name__ == '__main__':
    main()
