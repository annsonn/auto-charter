Audio → MIDI → Clone Hero Chart Workflow

Overview
- Input: MP3/WAV file or YouTube URL
- Output (automated): Per-instrument MIDIs (bass, lead), a merged multitrack MIDI with canonical PART names
- Output (assisted/manual): Clone Hero .chart refined in Moonscraper with difficulty reductions via CAT

Prereqs
- Windows 10 with Docker Desktop + WSL2 enabled
- Recommended Docker resources: 4–8 vCPU, 4–8 GB RAM

Build
- From repo root:
  - docker build -t ch-midi .

Run: Convert Audio → Stems → MIDIs → Merged MIDI
Options
- Lead selection:
  - --lead vocals (default) or --lead other
  - This determines which stem becomes PART GUITAR
- Drums:
  - --drums skip (default) or --drums basic
  - Basic Pitch is not suited for drums; default keeps drums off to avoid noisy results
- YouTube URL input:
  - Pass a YouTube URL instead of a file path
  - Pipeline uses yt-dlp internally to download/convert

Windows options
- Recommended:
  - .\process_songs.bat
    - No args: processes all MP3/WAV in songs\
    - With args: pass specific files or paths
- Manual:
  - cmd.exe:
    - docker run --rm -v "%cd%":/work ch-midi python /usr/local/bin/pipeline.py "songs\YourSong.mp3" --out out --lead vocals --drums skip
  - PowerShell:
    - docker run --rm -v "${PWD}:/work" ch-midi python /usr/local/bin/pipeline.py "songs/YourSong.mp3" --out out --lead vocals --drums skip
- YouTube input:
  - docker run --rm -v "%cd%":/work ch-midi python /usr/local/bin/pipeline.py "https://www.youtube.com/watch?v=XXXXXXXX" --out out --lead vocals

Outputs
- separated/htdemucs/<SongName>/
  - vocals.wav, bass.wav, drums.wav, other.wav
- out/<SongName>/
  - bass/bass_basic_pitch.mid
  - vocals/vocals_basic_pitch.mid or other/other_basic_pitch.mid
  - merged.mid (multitrack; canonical track names; PPQ preserved)
- Track names in merged.mid:
  - Lead stem → PART GUITAR
  - Bass stem → PART BASS
  - Optional non-lead (vocals/other) → PART RHYTHM (only included if transcribed)
  - PART DRUMS only included if a drums MIDI was actually generated

Analyze and normalize the multitrack MIDI (optional but recommended)
- Goal: Inspect timing/structure, auto-guess parts, and optionally write a normalized copy with canonical house names

Run MIDI Scout
- python tools/midi_scout.py out/<SongName>/merged.mid --out out/<SongName>/summary.json --normalize out/<SongName>/normalized.mid
- Summarizes:
  - Global timing: ppq, tempo map, time signatures, key signatures (if present)
  - Tracks: names, instrument names, channels, programs
  - Notes: count, pitch range, drum vs non-drum, median IOI (beats) for density
  - Heuristics: house_guess mapping to PART GUITAR/BASS/DRUMS/KEYS/VOCALS
  - Collisions and issues:
    - Missing parts, no tempo events, too many tempo changes, mis-channeled drums, zero-note files
- Normalization:
  - If there are unique guesses with no collisions, normalized.mid writes canonical PART names to tracks without changing timing
  - If collisions or ambiguity exist, it prints warnings; choose best manually or keep original

Acceptance checks (suggested)
- Fail if no_notes_on_any_track in summary.json. Likely wrong file.
- Warn if no_tempo_events_found or too_many_tempo_changes (>50). Might be corrupted export or unnecessary tempo bumps.
- Warn if a drums-like track has zero drum_notes (mis-channeled drums).
- Warn if normalized_parts_present is missing PART GUITAR or PART BASS (or PART DRUMS if you expect it).

Auto-Chart: MIDI → .chart via MIDI-CH
- Tool: https://github.com/TheNathannator/MIDI-CH
- Inputs:
  - Use normalized.mid if available, otherwise merged.mid
  - You can also feed separate part MIDIs if desired
- Expected behavior:
  - Converts multitrack MIDI to Clone Hero 5-lane .chart
  - Flags suspect areas for cleanup
- Output target:
  - charts/<SongFolder>/notes.chart

Moonscraper refinement
- Tool: https://github.com/Fireboyd78/Moonscraper
- Prepare a chart folder:
  - charts/<SongFolder>/
    - notes.chart (from MIDI-CH)
    - audio.(ogg|mp3) (source audio used for Demucs; consider using a mixed version, not stems)
    - song.ini (see template below)
    - album.png (optional)
- In Moonscraper:
  - Verify sync against audio; adjust BPM map if needed
  - Fix flagged sections from MIDI-CH
  - Ensure playability: hand shapes, chord choices, avoid excessive awkward patterns
  - Events:
    - Sections: INTRO, VERSE, PRE-CHORUS, CHORUS, SOLO, BRIDGE, OUTRO, etc.
    - Star Power: place fairly every ~15–25 seconds, avoid overlap with extremely dense parts
    - Optional: Crowd events, lyrics/markers (if working with PART VOCALS separately)
  - Save back to notes.chart

Difficulty reductions (Expert → Hard/Medium/Easy)
- Toolset: C3 Automation Tools (CAT) in REAPER
  - https://github.com/C3UOfficial/c3
- Workflow:
  - Import your Expert chart/MIDI into REAPER
  - Use CAT to generate reductions to H/M/E automatically, tweak thresholds if needed
  - Export and re-import to Moonscraper if you want to polish patterns/sections
- Alternative:
  - Manual pruning in Moonscraper
  - General rule of thumb: reduce density, simplify chord shapes, remove fast fills

Packaging for Clone Hero
- charts/<SongFolder>/
  - notes.chart
  - audio.ogg or audio.mp3 (ogg preferred)
  - song.ini
  - album.png (optional)
- Minimal song.ini template:
  - [song]
  - name = Your Song Title
  - artist = Artist Name
  - album = Album Name
  - year = 2025
  - charter = YourName
  - delay = 0
  - offset = 0
  - preview_start_time = 60
  - diff_guitar = 6
  - diff_bass = 5
  - diff_drums = 5
- Drop the folder into Clone Hero’s songs/ directory for testing

House conventions to enforce
- Track names:
  - PART GUITAR, PART BASS, PART DRUMS, PART KEYS (optional), PART VOCALS (optional)
- Drums on MIDI channel 10 (index 9)
- One tempo map (first/global track is fine). Keep PPQ consistent across repo (e.g., 480 or 960)
- At most one of each of the main parts; merge or choose the best candidate if duplicates exist
- Use MIDI Scout to detect collisions and normalize where safe

Tips
- If Demucs struggles, try demucs model variations (e.g., --model htdemucs_ft). Current default is htdemucs.
- If performance is slow, reduce Docker resource usage or process fewer songs concurrently.
- For synth-heavy tracks, set --lead other. For vocal-driven melody, use --lead vocals.

Quick reference: common commands
- Build: docker build -t ch-midi .
- Process a local file: docker run --rm -v "%cd%":/work ch-midi python /usr/local/bin/pipeline.py "songs\MySong.mp3" --out out --lead vocals --drums skip
- Process a YouTube URL: docker run --rm -v "%cd%":/work ch-midi python /usr/local/bin/pipeline.py "https://youtu.be/XXXXXXXX" --out out --lead other
- Run analyzer: python tools/midi_scout.py out/MySong/merged.mid --out out/MySong/summary.json --normalize out/MySong/normalized.mid
- Import into MIDI-CH: follow the MIDI-CH README; use normalized.mid if available
