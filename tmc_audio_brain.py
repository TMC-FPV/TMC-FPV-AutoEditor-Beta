"""Offline Audio Brain event interpretation extracted from TMC-FPV Audio Event Interpreter v0.2.7."""
import math

def smooth(vals):
    if len(vals) < 3:
        return list(vals)
    return [vals[0] * 0.25 + vals[1] * 0.5 + vals[2] * 0.25] + [vals[i - 1] * 0.25 + vals[i] * 0.5 + vals[i + 1] * 0.25 for i in range(1, len(vals) - 1)] + [vals[-3] * 0.25 + vals[-2] * 0.5 + vals[-1] * 0.25]

def norm(vals):
    lo, hi = (min(vals), max(vals))
    if hi - lo < 1e-09:
        return [0.5] * len(vals)
    return [(v - lo) / (hi - lo) for v in vals]

def classify(report):
    """v0.2.3: interpret trajectories, plateaus and transitions separately."""
    segs = report['segments_10s']
    n = len(segs)
    if not n:
        return {'events': [], 'metrics': {}}
    raw_rms = [float(s['rms_mean']) for s in segs]
    raw_flux = [float(s['spectral_flux_mean']) for s in segs]
    raw_cent = [float(s['spectral_centroid_hz']) for s in segs]
    rms, flux, cent = (smooth(raw_rms), smooth(raw_flux), smooth(raw_cent))
    nr, nf, nc = (norm(rms), norm(flux), norm(cent))
    bandkeys = ('bass_20_150', 'low_mid_150_500', 'high_mid_500_2000', 'high_2k_5k')
    shares = []
    for seg in segs:
        b = seg.get('texture_band_energy', {})
        vals = [max(0, float(b.get(k, 0))) for k in bandkeys]
        total = sum(vals) or 1
        shares.append([v / total for v in vals])

    def bdist(a, b):
        return sum((abs(x - y) for x, y in zip(shares[a], shares[b])))
    events = []

    def add(a, b, label, conf, why, kind='sustain'):
        a = max(0, min(n - 1, a))
        b = max(a, min(n - 1, b))
        events.append({'start': float(segs[a]['start_s']), 'end': float(segs[b]['end_s']), 'label': label, 'confidence': max(0.4, min(0.94, conf)), 'why': why, 'kind': kind})
    quiet = [nr[i] <= 0.23 and nf[i] <= 0.3 for i in range(n)]
    i = 0
    while i < n:
        if quiet[i]:
            j = i
            while j + 1 < n and quiet[j + 1]:
                j += 1
            if j - i + 1 >= 2:
                add(i, j, 'BREATHER', 0.7 + min(0.12, (1 - sum(nr[i:j + 1]) / (j - i + 1)) * 0.12), 'Sustained passage with low relative energy and low activity.')
            i = j + 1
        else:
            i += 1
    for i in range(1, n):
        fall = nr[i - 1] - nr[i]
        if nr[i - 1] >= 0.52 and fall >= 0.24:
            add(i, i, 'DROP / RELEASE', 0.68 + min(0.18, fall * 0.38), f'Energy falls sharply ({nr[i - 1]:.2f} to {nr[i]:.2f} relative); transition marker.', 'marker')
    slopes = [nr[i] - nr[i - 1] for i in range(1, n)]
    candidates = []
    i = 0
    while i < len(slopes):
        if slopes[i] >= 0.035:
            j = i
            while j + 1 < len(slopes) and slopes[j + 1] >= 0.035:
                j += 1
            a = max(0, i)
            b = min(n - 1, j + 1)
            segsl = slopes[i:j + 1]
            net = nr[b] - nr[a]
            if b - a >= 2 and net >= 0.18 and (len(segsl) >= 2):
                candidates.append((a, b, net))
            i = j + 1
        else:
            i += 1
    builds = list(candidates)
    for a, b, net in builds:
        q_overlap = [k for k in range(a, b + 1) if quiet[k]]
        if q_overlap:
            quiet_end = max(q_overlap)
            a = quiet_end + 1
            label = 'REBUILD'
        else:
            recent_quiet = [k for k in range(max(0, a - 3), a) if quiet[k]]
            label = 'REBUILD' if recent_quiet else 'BUILD'
            if recent_quiet:
                a = max(a, recent_quiet[-1] + 1)
        if b - a >= 1:
            add(a, b, label, 0.67 + min(0.19, net * 0.3), f'Directional build confirmed: net relative energy rise {net:.2f}, with sustained positive trend.')
    plateau = []
    i = 0
    while i < n:
        if nr[i] >= 0.72:
            j = i
            while j + 1 < n and nr[j + 1] >= 0.72 and (abs(nr[j + 1] - nr[j]) <= 0.22):
                j += 1
            if j - i + 1 >= 2 and max(nr[i:j + 1]) - min(nr[i:j + 1]) <= 0.24:
                plateau.append((i, j))
            i = j + 1
        else:
            i += 1
    for a, b in plateau:
        add(a, b, 'HIGH ENERGY', 0.68 + min(0.18, sum(nr[a:b + 1]) / (b - a + 1) * 0.18), 'Sustained high relative energy with limited change; classified as intensity plateau, not a build.')
    peak_candidates = []
    for i in range(n):
        left = nr[i - 1] if i > 0 else nr[i]
        right = nr[i + 1] if i < n - 1 else nr[i]
        prominence = nr[i] - min(left, right)
        if nr[i] >= 0.78 and nr[i] >= left and (nr[i] >= right) and (prominence >= 0.12 or nr[i] >= 0.94):
            peak_candidates.append(i)
    groups = []
    for idx in peak_candidates:
        if groups and idx <= groups[-1][-1] + 1:
            groups[-1].append(idx)
        else:
            groups.append([idx])
    for g in groups:
        p = max(g, key=lambda x: nr[x])
        add(p, p, 'PEAK', 0.69 + min(0.2, nr[p] * 0.2), f'Local high point ({nr[p]:.2f} relative), considered in context of surrounding energy.', 'marker')
    tex = []
    for i in range(1, n):
        cshift = abs(nc[i] - nc[i - 1])
        bshift = bdist(i, i - 1)
        if cshift >= 0.3 or bshift >= 0.58:
            tex.append((i, 0.62 + min(0.22, max(cshift, bshift * 0.45)), cshift, bshift))
    groups = []
    for t in tex:
        if groups and t[0] <= groups[-1][-1][0] + 1:
            groups[-1].append(t)
        else:
            groups.append([t])
    for g in groups:
        mid = round((g[0][0] + g[-1][0]) / 2)
        confidence = max((x[1] for x in g))
        add(mid, mid, 'TEXTURE SHIFT', confidence, f'Timbre transition marker; centroid/band-balance changed over {len(g)} adjacent window(s).', 'marker')
    if n >= 2 and nr[-1] <= 0.25 and (nr[-2] >= 0.48):
        add(n - 1, n - 1, 'ENDING / FADE', 0.68, 'Final section retreats to low energy with track-ending context.', 'marker')
    sust = [e for e in events if e['kind'] == 'sustain']
    markers = [e for e in events if e['kind'] == 'marker']
    merged = []
    for e in sorted(sust, key=lambda x: (x['start'], x['label'])):
        prior = next((m for m in reversed(merged) if m['label'] == e['label'] and e['start'] <= m['end'] + 1), None)
        if prior:
            prior['end'] = max(prior['end'], e['end'])
            prior['confidence'] = max(prior['confidence'], e['confidence'])
        else:
            merged.append(dict(e))
    for rb in [x for x in merged if x['label'] == 'REBUILD']:
        for b in [x for x in merged if x['label'] == 'BUILD']:
            if b['start'] < rb['end'] and b['end'] > rb['start']:
                if b['start'] < rb['start']:
                    b['end'] = rb['start']
                else:
                    b['start'] = rb['end']
    for p in [x for x in merged if x['label'] == 'HIGH ENERGY']:
        for b in [x for x in merged if x['label'] in ('BUILD', 'REBUILD')]:
            if b['start'] < p['end'] and b['end'] > p['start'] and (b['end'] > p['start']):
                if b['end'] > p['start']:
                    b['end'] = p['start']
    merged = [e for e in merged if e['end'] >= e['start'] and e['end'] - e['start'] >= 9]
    out = merged + markers
    out.sort(key=lambda x: (x['start'], x['label']))
    return {'events': out, 'metrics': {'rms_norm': nr, 'flux_norm': nf, 'centroid_norm': nc, 'raw_rms': rms, 'raw_flux': flux, 'raw_centroid': cent}}

def editorial_layer(raw_events):
    """Turn raw detections into editor-facing progressions and sequences.

    Instant markers remain markers. Texture shifts are treated as support notes
    rather than headline events. Sequence grouping is intentionally conservative.
    """
    events = [dict(e) for e in raw_events]
    events.sort(key=lambda e: (e['start'], e['end'], e['label']))
    texture = [e for e in events if e['label'] == 'TEXTURE SHIFT']
    primary = [e for e in events if e['label'] != 'TEXTURE SHIFT']
    used = set()
    out = []

    def overlaps_or_near(a, b, gap=12):
        return b['start'] <= a['end'] + gap and b['end'] >= a['start'] - gap

    def conf_for(items):
        return sum((float(e.get('confidence', 0.7)) for e in items)) / max(1, len(items))

    def supporting(a, b):
        return [t for t in texture if a - 12 <= t['start'] <= b + 12]
    drops = [e for e in primary if e['label'] == 'DROP / RELEASE']
    breathers = [e for e in primary if e['label'] == 'BREATHER']
    rebuilds = [e for e in primary if e['label'] == 'REBUILD']
    for d in drops:
        b = next((x for x in breathers if d['end'] <= x['start'] and x['start'] - d['end'] <= 25), None)
        r = next((x for x in rebuilds if b and b['end'] <= x['start'] and (x['start'] - b['end'] <= 35)), None)
        if b and r:
            seq = [d, b, r]
            out.append({'start': d['start'], 'end': r['end'], 'label': 'RELEASE → BREATHER → REBUILD', 'confidence': conf_for(seq), 'why': 'A fall in energy is followed by a low-activity passage, then a return of directional energy. ' + ' | '.join((x['label'] + ': ' + x['why'] for x in seq)), 'kind': 'sequence', 'subevents': [x['label'] for x in seq], 'support': [t['why'] for t in supporting(d['start'], r['end'])]})
            used.update((id(x) for x in seq))
    for build in [e for e in primary if e['label'] in ('BUILD', 'REBUILD') and id(e) not in used]:
        nearby_peaks = [p for p in primary if p['label'] == 'PEAK' and id(p) not in used and (build['start'] - 5 <= p['start'] <= build['end'] + 15)]
        nearby_plateaus = [h for h in primary if h['label'] == 'HIGH ENERGY' and id(h) not in used and overlaps_or_near(build, h, 10)]
        chosen = []
        if nearby_peaks:
            chosen.append(min(nearby_peaks, key=lambda p: abs(p['start'] - build['end'])))
        if nearby_plateaus:
            chosen.extend(nearby_plateaus)
        if chosen:
            members = [build] + chosen
            start = min((x['start'] for x in members))
            end = max((x['end'] for x in members))
            label = 'BUILD → CLIMAX' if nearby_peaks else 'BUILD → HIGH ENERGY'
            out.append({'start': start, 'end': end, 'label': label, 'confidence': conf_for(members), 'why': 'Editorial progression: ' + ', '.join((x['label'] for x in members)) + '. ' + ' | '.join((x['why'] for x in members)), 'kind': 'sequence', 'subevents': [x['label'] for x in members], 'support': [t['why'] for t in supporting(start, end)]})
            used.update((id(x) for x in members))
        else:
            out.append(dict(build))
            used.add(id(build))
    for e in primary:
        if id(e) not in used and (not any((x is e for x in out))):
            out.append(dict(e))
    out.sort(key=lambda e: (e['start'], e['label']))
    return (out, texture)

def musical_sections(report, metrics):
    """v0.2.7: mutually-exclusive track-wide sections for a clean hierarchy.


    Sections cover the entire track, do not overlap, and absorb short noisy states.
    Detailed editorial events remain nested beneath these section parents in the UI.
    """
    rms = metrics.get('rms_norm', [])
    flux = metrics.get('flux_norm', [])
    segs = report.get('segments_10s', [])
    if not rms or not segs:
        return []
    n = min(len(rms), len(segs))
    states = []
    for i in range(n):
        e = float(rms[i])
        a = float(flux[i]) if i < len(flux) else 0.5
        prev = float(rms[i - 1]) if i else e
        nxt = float(rms[min(n - 1, i + 1)])
        lookahead = float(rms[min(n - 1, i + 3)]) - float(rms[max(0, i - 1)])
        if i and prev >= 0.55 and (prev - e >= 0.24):
            state = 'RELEASE'
        elif e <= 0.24 and a <= 0.32:
            state = 'LOW ENERGY'
        elif e >= 0.74 and abs(e - prev) <= 0.2:
            state = 'SUSTAINED INTENSITY'
        elif i and states[-1] in ('LOW ENERGY', 'RELEASE') and (e > 0.28) and (lookahead >= 0.16):
            state = 'RECOVERY'
        elif lookahead >= 0.24 and e >= 0.22 and (a >= 0.16):
            state = 'BUILDING'
        else:
            state = 'STEADY / TRANSITION'
        states.append(state)
    labels = list(states)

    def make_runs(values):
        result = []
        i = 0
        n = len(values)
        while i < n:
            j = i
            while j + 1 < n and values[j + 1] == values[i]:
                j += 1
            result.append([i, j, values[i]])
            i = j + 1
        return result
    changed = True
    while changed:
        changed = False
        rs = make_runs(labels)
        for k, (a, b, label) in enumerate(rs):
            if b - a + 1 >= 2:
                continue
            neighbours = []
            if k > 0:
                neighbours.append(rs[k - 1])
            if k + 1 < len(rs):
                neighbours.append(rs[k + 1])
            if not neighbours:
                continue
            target = max(neighbours, key=lambda r: (r[1] - r[0] + 1, r[2] != 'STEADY / TRANSITION'))[2]
            for q in range(a, b + 1):
                labels[q] = target
            changed = True
            break
    rs = make_runs(labels)
    out = []
    for a, b, label in rs:
        start = float(segs[a].get('start_s', a * 10))
        end = float(segs[b].get('end_s', (b + 1) * 10))
        confidence = {'LOW ENERGY': 0.78, 'BUILDING': 0.76, 'SUSTAINED INTENSITY': 0.76, 'RELEASE': 0.72, 'RECOVERY': 0.75, 'STEADY / TRANSITION': 0.7}.get(label, 0.7)
        out.append({'start': start, 'end': end, 'label': label, 'confidence': confidence, 'why': f'Track section across {b - a + 1} windows; smoothed relative energy/activity classification.', 'kind': 'section'})
    merged = []
    for sec in out:
        if merged and merged[-1]['label'] == sec['label'] and (sec['start'] <= merged[-1]['end'] + 0.01):
            merged[-1]['end'] = sec['end']
        else:
            merged.append(dict(sec))
    return merged
