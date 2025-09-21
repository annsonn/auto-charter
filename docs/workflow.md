Audio ? MIDI ? Clone Hero Chart Workflow
========================================

This guide drills into every stage of the toolchain the batch scripts orchestrate. If you just want the defaults, run `./run_all.bat` from PowerShell and skip to **Post-processing**. The remainder of this document explains what each stage does, the files it produces, and how to customise the pipeline.

Prerequisites
-------------
- Windows 10/11 with Docker Desktop (WSL 2 backend)
- Adequate Docker resources (4–8 vCPU, 6–8?GB RAM)
- PowerShell (included with Windows)
- MP3/WAV source material placed in `songs/`

Stage 0: One-shot automation
----------------------------
### `./run_all.bat`
Runs the full stack:
1. `process_songs.bat` – rebuilds the `ch-midi` image, clears `out/` and `separated/`, then generates fresh stems and MIDIs.
2. `convert_opus.bat` – rebuilds `ffmpeg-opus` and creates an Opus copy of every track in `opus-output/`.
3. `auto-chart.bat` – rebuilds `midi-ch-batch`, feeds each `merged.mid` to MIDI-CH, copies `notes.mid`, looks for `<Song>.opus`/`.ogg` and stores it as `song.opus`, then stages chart folders under `charts/`.

Each script stops on failure. Rerun the failed stage (or `run_all.bat`) after correcting the issue.

Stage 1: Process songs
----------------------
### Script
```
./process_songs.bat [optional song paths]
```

### What happens
- Builds/updates the `ch-midi` Docker image.
- For every MP3/WAV in `songs/` (or supplied on the command line):
  1. **Demucs** separates the song into `vocals`, `bass`, `drums`, and `other` stems.
  2. **Basic Pitch** converts selected stems to MIDI (bass is always processed; vocals/other depends on `--lead`; drums only with `--drums basic`).
  3. The script merges available MIDI tracks into `merged.mid` and writes a per-part map.

### Output
- `separated/htdemucs/<Song>/` – WAV stems.
- `out/<Song>/`
  - `bass/bass_basic_pitch.mid`
  - `vocals_basic_pitch.mid` or `other_basic_pitch.mid`
  - `merged.mid` (multi-track, canonical PART names)
  - `notes.mid` (copy created in Stage 3)

### Customisation
Edit the environment variables at the top of `process_songs.bat`:
- `LEAD=vocals|other`
- `DRUMS=skip|basic`
- `OUT_ROOT=...`
Manual options: `docker run --rm -v "${PWD}:/work" ch-midi python /usr/local/bin/pipeline.py --help`

Stage 2: Convert audio to Opus
------------------------------
### Script
```
./convert_opus.bat [optional song paths]
```

### What happens
- Builds/updates the `ffmpeg-opus` image.
- Uses a PowerShell helper to enumerate MP3s safely (handles spaces/parentheses).
- Invokes ffmpeg (`libopus`, 160?kbps, 48?kHz) for every source file.

### Output
- `opus-output/<Song>.opus`

### Customisation
- Provide explicit paths to convert a subset: `./convert_opus.bat "songs/My Song.mp3"`
- Tweak the bitrate or target extension inside `tools/convert_opus.ps1` if desired.

Stage 3: Auto-chart with MIDI-CH
--------------------------------
### Script
```
./auto-chart.bat [--input DIR] [--output DIR] [--image NAME] [--opus DIR]
```

### What happens
- Builds/updates `midi-ch-batch` (Node + Puppeteer + Chrome dependencies).
- Launches headless Chrome, loads the MIDI-CH auto page, uploads every `merged.mid` under the input directory, and captures the generated `.chart` file(s).
- Copies each song’s `merged.mid` to `notes.mid` and pulls `opus-output/<Song>.opus` (or `.ogg`) into the chart folder as `song.opus` when available.
- Injects basic metadata (Name/Artist) into `song.ini` and `notes.chart` using the folder name (`Artist - Title` expected).

### Output
- `charts/<Song>/`
  - `notes.chart` (raw MIDI-CH export – inspect in Moonscraper)
  - `notes.mid` (multi-track MIDI copy)
  - `song.opus` (from Stage 2, if found)
  - `song.ini` (auto-populated with title/artist and MIDI-CH defaults)

### Customisation
- Use `--help` to inspect CLI options.
- Override `--opus` if your Opus files live elsewhere (e.g. `--opus /work/audio/opus`).
- Add `-- --lead other` (after `--`) to forward extra arguments to the Node script (rarely needed).

Post-processing & polishing
---------------------------
1. **Inspect the auto-chart folder** – Validate the generated chart in Moonscraper; tweak timing, event markers, and note patterns.
2. **Difficulty reductions** – Use C3 Automation Tools (CAT) in REAPER to generate Hard/Medium/Easy based on the Expert chart.
3. **Packaging** – Ensure the chart folder contains `notes.chart`, `song.opus` (or `.ogg`), `song.ini`, and optional art (`album.png`). Zip it or copy into Clone Hero’s `songs/` directory for testing.

Troubleshooting
---------------
- **Docker build failures** – Restart Docker Desktop or allocate more resources. Each script echoes the `docker build` output.
- **Demucs timing/stem issues** – Re-run Stage 1 with alternative options (e.g., change `LEAD`, enable drums) or clean up the stems manually.
- **Basic Pitch errors referencing SciPy** – Ensure Stage 1 rebuilds the container (SciPy 1.9.3 is bundled).
- **Opus copy missing** – Confirm Stage 2 ran and `opus-output/<Song>.opus` exists before Stage 3. The auto-chart script logs when it cannot find an Opus candidate.
- **MIDI-CH Puppeteer timeouts** – Running `auto-chart.bat` again usually recovers. Long songs may need more than the default 120-second window; adjust the timeout in `tools/auto_chart_batch.js` if necessary.

Reference
---------
- Demucs: <https://github.com/facebookresearch/demucs>
- Basic Pitch: <https://github.com/spotify/basic-pitch>
- MIDI-CH Autocharter: <https://github.com/EFHIII/midi-ch>
- Moonscraper: <https://github.com/Fireboyd78/Moonscraper>
- C3 Automation Tools: <https://github.com/C3UOfficial/c3>

