# tools/midi_scout.py
# Usage:
#   python tools/midi_scout.py path/to/input.mid --out summary.json --normalize out/normalized.mid
#
# Requires: pip install mido

import argparse, json
from collections import defaultdict, Counter
import mido
import statistics

DRUM_CH = 9  # MIDI channel 10

HOUSE_NAMES = {
    'guitar': 'PART GUITAR',
    'bass': 'PART BASS',
    'drums': 'PART DRUMS',
    'keys': 'PART KEYS',
    'vocals': 'PART VOCALS',
}

CANDIDATE_MAP = {
    # heuristics to map incoming track names to your house names
    'guitar': ['guitar', 'lead', 'egtr', 'electric', 'melody', 'lead gtr'],
    'bass':   ['bass', 'bass gtr'],
    'drums':  ['drums', 'kit', 'percussion'],
    'keys':   ['keys', 'piano', 'synth', 'rhodes', 'organ'],
    'vocals': ['vocals', 'vox', 'singer', 'lead vocal'],
}

def classify_name(name: str):
    if not name:
        return None
    low = name.lower()
    for part, candidates in CANDIDATE_MAP.items():
        if any(c in low for c in candidates):
            return HOUSE_NAMES[part]
    return None

def analyze(path):
    mid = mido.MidiFile(path)
    ppq = mid.ticks_per_beat

    tempo_changes = [(0, 500000)]
    timesig_changes = [(0, (4,4))]
    key_sigs = []
    markers, lyrics, texts = [], [], []
    tracks = []
    explicit_tempo_events = 0

    for ti, track in enumerate(mid.tracks):
        abs_tick = 0
        notes_on = defaultdict(list)
        note_list = []
        channels, programs = set(), set()
        track_name, inst_name = None, None

        for msg in track:
            abs_tick += msg.time
            if msg.type == 'track_name':
                track_name = msg.name
            elif msg.type == 'instrument_name':
                inst_name = msg.name
            elif msg.type == 'set_tempo':
                tempo_changes.append((abs_tick, msg.tempo))
                explicit_tempo_events += 1
            elif msg.type == 'time_signature':
                timesig_changes.append((abs_tick, (msg.numerator, msg.denominator)))
            elif msg.type == 'key_signature':
                key_sigs.append({'tick': abs_tick, 'key': getattr(msg, 'key', None)})
            elif msg.type == 'marker':
                markers.append({'track': ti, 'tick': abs_tick, 'text': msg.text})
            elif msg.type == 'lyrics':
                lyrics.append({'track': ti, 'tick': abs_tick, 'text': msg.text})
            elif msg.type == 'text':
                texts.append({'track': ti, 'tick': abs_tick, 'text': msg.text})
            elif msg.type == 'program_change':
                programs.add(msg.program); channels.add(msg.channel)
            elif msg.type == 'control_change':
                channels.add(msg.channel)
            elif msg.type == 'pitchwheel':
                channels.add(msg.channel)
            elif msg.type == 'note_on':
                channels.add(msg.channel)
                if msg.velocity > 0:
                    notes_on[(msg.channel, msg.note)].append((abs_tick, msg.velocity))
                else:
                    if notes_on[(msg.channel, msg.note)]:
                        start, vel = notes_on[(msg.channel, msg.note)].pop(0)
                        note_list.append((msg.channel, msg.note, start, abs_tick, vel))
            elif msg.type == 'note_off':
                channels.add(msg.channel)
                if notes_on[(msg.channel, msg.note)]:
                    start, vel = notes_on[(msg.channel, msg.note)].pop(0)
                    note_list.append((msg.channel, msg.note, start, abs_tick, vel))

        # close open notes
        for (ch, pitch), starts in list(notes_on.items()):
            for start, vel in starts:
                note_list.append((ch, pitch, start, abs_tick, vel))

        pitches = [n[1] for n in note_list]
        drum_notes = sum(1 for n in note_list if n[0]==DRUM_CH)
        total_notes = len(note_list)

        # Compute median IOI (beats) from note start times
        starts = sorted(n[2] for n in note_list)
        ioi_beats = None
        if len(starts) >= 2:
            diffs = [(starts[i+1] - starts[i]) / ppq for i in range(len(starts)-1) if (starts[i+1] - starts[i]) > 0]
            if diffs:
                ioi_beats = round(statistics.median(diffs), 4)

        tracks.append({
            'index': ti,
            'track_name': track_name,
            'instrument_name': inst_name,
            'channels': sorted(channels),
            'programs': sorted(programs),
            'notes': total_notes,
            'drum_notes': drum_notes,
            'non_drum_notes': total_notes - drum_notes,
            'min_pitch': min(pitches) if pitches else None,
            'max_pitch': max(pitches) if pitches else None,
            'ioi_median_beats': ioi_beats,
            'house_guess': classify_name(track_name or '') or classify_name(inst_name or ''),
        })

    tempo_changes.sort(key=lambda x: x[0])
    timesig_changes.sort(key=lambda x: x[0])

    # Samples
    lyrics_sample = [l['text'] for l in lyrics[:5]]
    texts_sample = [t['text'] for t in texts[:5]]

    # Collisions on guesses
    guess_map = defaultdict(list)
    for row in tracks:
        if row['house_guess']:
            guess_map[row['house_guess']].append(row['index'])
    collisions = {k: v for k, v in guess_map.items() if len(v) > 1}

    # Simulate normalization assignments (unique names only)
    used = set()
    assignments = []
    for row in tracks:
        guess = row['house_guess']
        assigned = None
        if guess and guess not in used:
            assigned = guess
            used.add(guess)
        assignments.append({'index': row['index'], 'assigned': assigned})

    parts_present = sorted(list(used))
    total_notes_all = sum(r['notes'] for r in tracks)

    issues = {'errors': [], 'warnings': []}
    if total_notes_all == 0:
        issues['errors'].append('no_notes_on_any_track')
    if explicit_tempo_events == 0:
        issues['warnings'].append('no_tempo_events_found')
    if explicit_tempo_events > 50:
        issues['warnings'].append(f'too_many_tempo_changes:{explicit_tempo_events}')
    for row in tracks:
        name = (row['track_name'] or '').upper() if row['track_name'] else ''
        if ((row['house_guess'] == 'PART DRUMS') or ('PART DRUMS' in name) or ('DRUM' in name)):
            if row['drum_notes'] == 0:
                issues['warnings'].append(f'mis_channeled_drums_track_index:{row["index"]}')
    desired = ['PART GUITAR', 'PART BASS', 'PART DRUMS']
    for d in desired:
        if d not in used:
            issues['warnings'].append(f'missing_{d.replace(" ", "_")}')

    analysis = {
        'file': path,
        'ppq': ppq,
        'num_tracks': len(mid.tracks),
        'tempo_changes': [{'tick': t, 'bpm': round(60_000_000/tus,3)} for t,tus in tempo_changes],
        'time_signatures': [{'tick': t, 'numerator': n, 'denominator': d} for t,(n,d) in timesig_changes],
        'key_signatures': key_sigs,
        'markers': markers,
        'lyrics_count': len(lyrics),
        'texts_count': len(texts),
        'lyrics_sample': lyrics_sample,
        'texts_sample': texts_sample,
        'explicit_tempo_events': explicit_tempo_events,
        'tracks': tracks,
        'normalized_assignments': assignments,
        'normalized_parts_present': parts_present,
        'collisions': collisions,
        'issues': issues,
    }
    return analysis, mid

def normalize_tracks(mid, analysis):
    """
    Return a copy of the MIDI with track names rewritten to house names when safe.
    Leaves timing/meta untouched.
    """
    out = mido.MidiFile(type=mid.type)
    out.ticks_per_beat = mid.ticks_per_beat
    used = set()

    for i, track in enumerate(mid.tracks):
        t = mido.MidiTrack()
        # pick house name if unique; else keep original
        orig_name = None
        house = None
        for row in analysis['tracks']:
            if row['index'] == i:
                orig_name = row['track_name']
                guess = row['house_guess']
                if guess and guess not in used:
                    house = guess
                    used.add(guess)
                break
        name_to_write = house or orig_name
        wrote_name = False

        for msg in track:
            if msg.type == 'track_name':
                if name_to_write and not wrote_name:
                    t.append(mido.MetaMessage('track_name', name=name_to_write, time=msg.time))
                    wrote_name = True
                else:
                    t.append(msg)
            else:
                t.append(msg)
        if not wrote_name and name_to_write:
            t.insert(0, mido.MetaMessage('track_name', name=name_to_write, time=0))
        out.tracks.append(t)

    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('midi', help='Input .mid')
    ap.add_argument('--out', help='Write JSON summary to path')
    ap.add_argument('--normalize', help='Write normalized MIDI to path')
    args = ap.parse_args()

    analysis, mid = analyze(args.midi)
    print(json.dumps(analysis, indent=2))

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2)

    if args.normalize:
        norm = normalize_tracks(mid, analysis)
        norm.save(args.normalize)

if __name__ == '__main__':
    main()
