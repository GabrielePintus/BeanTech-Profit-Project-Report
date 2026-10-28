#!/usr/bin/env python3
"""Render rounded orthogonal routes with direction-consistent shared trunks."""
from pathlib import Path
import json
import math
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'figures/documented-production-graph.dot'
OUTPUT = SOURCE.with_suffix('.pdf')


def simplify(points):
    result = []
    for p in points:
        if result and math.dist(p, result[-1]) < 0.01:
            continue
        if len(result) >= 2:
            a, b = result[-2:]
            same_x = abs(a[0]-b[0]) < .01 and abs(b[0]-p[0]) < .01
            same_y = abs(a[1]-b[1]) < .01 and abs(b[1]-p[1]) < .01
            if (same_x or same_y) and sum((b[k]-a[k])*(p[k]-b[k]) for k in (0, 1)) >= 0:
                result.pop()
        result.append(p)
    return result


def rounded_controls(points, radius=5.0):
    points = simplify(points)
    controls, current = [points[0]], points[0]
    for i in range(1, len(points)-1):
        a, p, b = points[i-1:i+2]
        la, lb = math.dist(a, p), math.dist(p, b)
        u = tuple((p[k]-a[k])/la for k in (0, 1))
        v = tuple((b[k]-p[k])/lb for k in (0, 1))
        # Radius is bounded by adjacent segments so short terminal legs remain valid.
        r = min(radius, la/3, lb/3)
        entry = tuple(p[k]-u[k]*r for k in (0, 1))
        exit = tuple(p[k]+v[k]*r for k in (0, 1))
        controls.extend([current, entry, entry])
        kappa = .5522847498
        controls.extend([
            tuple(entry[k]+u[k]*r*kappa for k in (0, 1)),
            tuple(exit[k]-v[k]*r*kappa for k in (0, 1)), exit,
        ])
        current = exit
    controls.extend([current, points[-1], points[-1]])
    return controls


def main():
    source = SOURCE.read_text()
    layout = json.loads(subprocess.check_output(['neato', '-n2', '-Tjson', str(SOURCE)]))
    nodes = {n['name']: n for n in layout['objects'] if 'pos' in n}
    ids = {n['_gvid']: n['name'] for n in nodes.values()}

    def center(name):
        return tuple(map(float, nodes[name]['pos'].split(',')))

    def port(name, side):
        x, y = center(name)
        w, h = float(nodes[name]['width'])*72, float(nodes[name]['height'])*72
        return {'e': (x+w/2, y), 'w': (x-w/2, y),
                's': (x, y-h/2), 'n': (x, y+h/2)}[side]

    routes = {}
    for e in layout['edges']:
        values = e['pos'].split()
        assert values[0].startswith('e,')
        tip = tuple(map(float, values[0][2:].split(',')))
        points = [tuple(map(float, v.split(','))) for v in values[1:]]
        routes[ids[e['tail']], ids[e['head']]] = tip, simplify(points)

    def connect(tail, head, side, corners, head_side='w', tail_offset=(0, 0)):
        start, tip = port(tail, side), port(head, head_side)
        start = start[0]+tail_offset[0], start[1]+tail_offset[1]
        dx, dy = {'w': (-7.5, 0), 'e': (7.5, 0),
                  'n': (0, 7.5), 's': (0, -7.5)}[head_side]
        base = tip[0]+dx, tip[1]+dy
        points = simplify([start, *corners, base])
        assert all(abs(a[0]-b[0]) < .01 or abs(a[1]-b[1]) < .01 for a, b in zip(points, points[1:])), (tail, head)
        routes[tail, head] = tip, points

    # The short incoming arrow marks the start without adding a visible phase.
    connect('production_start', 'treno', 'e', [])

    # BANCHI and HPT share the descending initial trunk from TRENOLUNA.
    # The BANCHI branch leaves that trunk and enters its west border.
    connect('treno', 'conf', 'e', [])
    _, banchi_y = port('banchi', 'w')
    treno_x, _ = port('treno', 's')
    connect('treno', 'banchi', 's', [(treno_x, banchi_y)])

    # Arrivals above and below PRONTO meet on the same axis. Their
    # vertical segments occupy disjoint halves, and the final eastbound leg is shared.
    _, ry = center('ready')
    for tail in ['conf', 'amrework', 'amqt']:
        _, sy = port(tail, 'e')
        bus = 780.0
        connect(tail, 'ready', 'e', [(bus, sy), (bus, ry)])
    connect('hptfirst', 'ready', 'e', [])
    hx, _ = port('hptfirst', 's')

    # All BANCHI outputs start at its east border and share one short
    # eastbound stem before branching to the optional operations/scrap.
    banchi_right, banchi_y = port('banchi', 'e')
    target_left = min(port(head, 'w')[0] for head in ['tag', 'raddr', 'mol', 'scrap'])
    branch_x = (banchi_right+target_left)/2
    for head in ['tag', 'raddr', 'mol', 'scrap']:
        _, target_y = center(head)
        connect('banchi', head, 'e', [(branch_x, banchi_y), (branch_x, target_y)])

    _, ay = center('amrework')
    for tail in ['banchi', 'tag', 'raddr', 'banchi2']:
        _, sy = port(tail, 'e')
        connect(tail, 'amrework', 'e', [(410.0, sy), (410.0, ay)])

    ax, _ = port('amrework', 's')
    hpt_x, _ = center('hptfirst')
    connect('amrework', 'hptfirst', 's', [(ax, 213.0), (hpt_x, 213.0)], head_side='n')
    for head, bus in [('lunaqt', 150.0), ('lfcd', 135.0)]:
        _, ty = center(head)
        connect('amrework', head, 's', [(ax, 213.0), (bus, 213.0), (bus, ty)])
    tx, _ = port('treno', 's')
    for head, bus in [('hptfirst', 40.0), ('lunaqt', 150.0), ('lfcd', 135.0)]:
        _, ty = center(head)
        connect('treno', head, 's', [(tx, ty), (bus, ty)])
    # Separate only the departure points on the HPT border. Each route
    # has one right-angle turn, without an extra lateral detour.
    _, qy = center('lunaqt')
    connect('hptfirst', 'lunaqt', 's', [(hx+4.5, qy)], tail_offset=(4.5, 0))
    _, lfc_y = center('lfcd')
    connect('hptfirst', 'lfcd', 's', [(hx-4.5, lfc_y)], tail_offset=(-4.5, 0))

    # Treatments meet symmetrically on the HPT axis. The two vertical
    # segments occupy opposite halves and share no counter-directed section.
    _, post_y = center('hptqt')
    treatment_exit, _ = port('lunaqt', 'e')
    hpt_entry, _ = port('hptqt', 'w')
    bus = (treatment_exit+hpt_entry)/2
    for tail in ['lunaqt', 'lfcd']:
        _, sy = port(tail, 'e')
        connect(tail, 'hptqt', 'e', [(bus, sy), (bus, post_y)])

    def halfway(tail, head):
        a, b = port(tail, 'e'), port(head, 'w')
        assert abs(a[1]-b[1]) < .01
        return (a[0]+b[0])/2, a[1]

    # The two final skips share the same side and final trunk. Positions are
    # derived from node borders, so no junction crowds a node or arrowhead.
    first_split, row_y = halfway('hptqt', 'raddrqt')
    second_split, _ = halfway('raddrqt', 'circoqt')
    final_join, _ = halfway('circoqt', 'amqt')
    connect('circoqt', 'amqt', 'e', [])
    connect('hptqt', 'amqt', 'e', [
        (first_split, row_y), (first_split, row_y-45.0),
        (final_join, row_y-45.0), (final_join, row_y),
    ])
    connect('raddrqt', 'amqt', 'e', [
        (second_split, row_y), (second_split, row_y-45.0),
        (final_join, row_y-45.0), (final_join, row_y),
    ])

    fmt = lambda p: f'{p[0]:.4f},{p[1]:.4f}'
    for (tail, head), (tip, points) in routes.items():
        pos = 'e,'+fmt(tip)+' '+' '.join(map(fmt, rounded_controls(points)))
        pattern = rf'(?m)^(\s*{tail}\s*->\s*{head})\s*;'
        source, count = re.subn(pattern, lambda m: m[1]+f' [pos="{pos}"];', source)
        assert count == 1, (tail, head, count)
    with tempfile.TemporaryDirectory(prefix='beantech-production-graph-') as tmp:
        routed = Path(tmp)/'routed.dot'
        routed.write_text(source)
        subprocess.run(['neato', '-n2', '-Tpdf', str(routed), '-o', str(OUTPUT)], check=True)
    print(f'Rendered {len(nodes)-1} phase nodes, {len(routes)-1} internal connections and the incoming start arrow.')


if __name__ == '__main__':
    main()
