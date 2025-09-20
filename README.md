# Audio → MIDI Toolchain for Clone Hero Charting

A Dockerized pipeline that converts MP3/WAV files to MIDI using open-source tools, optimized for CPU-only execution on Windows hosts.

## Features

- **Stem Separation**: Uses Demucs (htdemucs model) to separate audio into vocals, bass, drums, and other
- **MIDI Transcription**: Spotify Basic Pitch for melody/bass transcription
- **Windows-friendly**: Designed for Docker Desktop + WSL2 on Windows 10
- **CPU-only**: No GPU required, runs efficiently on AMD/Intel processors

## Prerequisites

- **Docker Desktop** with WSL2 backend enabled
- **Recommended Docker settings**:
  - 4-8 vCPU cores allocated
  - 4-8 GB RAM allocated
  - Enable "Use the WSL 2 based engine"

## Quick Start

### 1. Build the Docker Image

```bash
docker build -t ch-midi .
```

**Note**: If you encounter "INTERNAL_ERROR" during build on Windows Docker Desktop, try:
1. Restart Docker Desktop
2. Increase Docker memory allocation to 8GB+
3. Use the alternative build method below

**Alternative Build Method** (if Docker build fails):
```bash
# Build with reduced memory usage
docker build --memory=4g -t ch-midi .
```

### 2. Prepare Your Audio

Place your MP3/WAV files in the `songs/` directory:

```
autocharter/
├── Dockerfile
├── pipeline.py
├── process_songs.bat
├── README.md
├── requirements.txt
└── songs/
    ├── G-DRAGON - TAKE ME (Official Audio).mp3
    └── G-DRAGON - HOME SWEET HOME (Official Audio) (feat. TAEYANG & DAESUNG).mp3
```

### 3. Run the Pipeline

**Easy Windows Method (Recommended):**
```cmd
.\process_songs.bat
```

**Manual Docker Commands:**

**Windows Command Prompt:**
```cmd
docker run --rm -v "%cd%":/work ch-midi python /usr/local/bin/pipeline.py "songs/YourSong.mp3" --out out/YourSong
```

**Windows PowerShell:**
```powershell
docker run --rm -v "${PWD}:/work" ch-midi python /usr/local/bin/pipeline.py "songs/YourSong.mp3" --out out/YourSong
```
## Full Workflow

### Option 1. Batch convert every song in `songs/`
1. Build the Docker image once: `docker build -t ch-midi .`
2. Drop your MP3/WAV files into `songs/`.
3. Run `.\process_songs.bat` from the repo root.
   - No arguments processes every `*.mp3`/`*.wav` in `songs/`.
   - Pass specific paths to process a subset, e.g. `.\process_songs.bat "songs\\My Song.mp3"`.
4. Inspect results in `out/<SongName>/` (MIDIs) and `separated/<model>/<SongName>/` (stems).
5. (Optional) Summarize and normalize the merged MIDI for charting:
   `python tools/midi_scout.py out/<SongName>/merged.mid --out out/<SongName>/summary.json --normalize out/<SongName>/normalized.mid`.

### Option 2. Start from a YouTube URL
1. Build the Docker image if you have not already: `docker build -t ch-midi .`.
2. Run the pipeline with the YouTube link:
   `docker run --rm -v "%cd%":/work ch-midi python /usr/local/bin/pipeline.py "https://youtu.be/XXXXXXXX" --out out/YouTubeSong --lead vocals --drums skip`.
   - The container downloads audio via `yt-dlp` into `songs/tmp_download.wav` before processing.
   - Adjust `--lead` (vocals|other) and `--drums` (skip|basic) as needed.
3. Collected outputs match the local workflow: MIDIs in `out/YouTubeSong/`, stems in `separated/<model>/tmp_download/`.
4. Rename or move `songs/tmp_download.*` if you want to keep the download for later runs.
5. (Optional) Run `tools/midi_scout.py` as above to review timing, track names, and write `normalized.mid` for MIDI-CH.

After either workflow, continue with the charting steps in `docs/workflow.md` (MIDI-CH -> Moonscraper -> CAT -> packaging).

## Command Line Options

```bash
python /usr/local/bin/pipeline.py <audio_or_url> [options]

Required:
  audio_or_url                Path to MP3/WAV under /work OR a YouTube URL

Options:
  --model MODEL               Demucs model (default: htdemucs)
  --out DIR                   Output directory (default: out)
  --lead {vocals,other}       Lead stem for transcription (default: vocals)
  --drums {skip,basic}        Drums transcription mode (default: skip)
```

Note:
- You can pass a YouTube URL directly as the first argument. The pipeline will download audio via yt-dlp and proceed.
- Drums are skipped by default because Basic Pitch is monophonic and not suited for drum transcription.

## Expected Output

After processing, you'll find:

```
out/
└─ <SongName>/
   ├─ bass/
   │   └─ bass_basic_pitch.mid      # Bass transcription
   └─ vocals/
       └─ vocals_basic_pitch.mid    # Lead transcription
```

### Example Output Structure:
```
out/
├── TAKE_ME_FINAL/
│   └── G-DRAGON - TAKE ME (Official Audio)/
│       ├── bass/
│       │   └── bass_basic_pitch.mid      # 15,085 bytes
│       └── vocals/
│           └── vocals_basic_pitch.mid    # 24,956 bytes
└── HOME_SWEET_HOME_FINAL/
    └── G-DRAGON - HOME SWEET HOME (Official Audio) (feat. TAEYANG & DAESUNG)/
        ├── bass/
        │   └── bass_basic_pitch.mid      # 34,157 bytes
        └── vocals/
            └── vocals_basic_pitch.mid    # 20,747 bytes
```

## Processing Steps

1. **Demucs Stem Separation**: Separates audio into bass, drums, vocals, and other stems
2. **Basic Pitch Transcription**: Converts bass and vocals stems to MIDI format
3. **Output Generation**: Creates individual MIDI files for each instrument

## Analyzer: MIDI Scout

A drop-in analyzer that inspects a multitrack MIDI for:
- Global timing: PPQ, tempo changes (tick+BPM), time signatures, key signatures
- Track inventory: names, instrument names, channels, program changes
- Per-track notes: count, pitch range, drum vs. non-drum (channel 10), median IOI (beats)
- Heuristics to map to house parts: PART GUITAR, PART BASS, PART DRUMS, PART KEYS, PART VOCALS
- Collisions and sanity checks (e.g., duplicates, missing parts, excessive tempo changes)

Usage:
```bash
python tools/midi_scout.py out/<SongName>/merged.mid --out out/<SongName>/summary.json --normalize out/<SongName>/normalized.mid
```

Behavior:
- Writes JSON summary with timing, tracks, stats, and warnings.
- If there are unique part guesses with no collisions, writes a normalized MIDI with canonical PART names (timing unchanged).
- Warnings:
  - no_tempo_events_found, too_many_tempo_changes, mis-channeled drums, missing PARTs, zero-note files.

Recommendation:
- Use normalized.mid with MIDI-CH Autocharter when available, otherwise use merged.mid.

See also: docs/workflow.md for the full end-to-end process.

## Examples

### Process a Single Song
```cmd
docker run --rm -v "%cd%":/work ch-midi python /usr/local/bin/pipeline.py "songs/MySong.mp3" --out out/MySong
```

### Process with Different Lead Stem
```cmd
docker run --rm -v "%cd%":/work ch-midi python /usr/local/bin/pipeline.py "songs/MySong.mp3" --lead other --out out/MySong
```

## Workflow Guide

A detailed end-to-end workflow (Audio → Stems → MIDIs → Merged MIDI → MIDI-CH → Moonscraper → CAT → Packaging) is provided in:
- docs/workflow.md

## Troubleshooting

### Docker Build Issues
If you encounter "INTERNAL_ERROR" during Docker build:

1. **Restart Docker Desktop** completely
2. **Increase memory allocation** to 8GB+ in Docker Desktop settings
3. **Try alternative build**:
   ```bash
   docker build --memory=4g -t ch-midi .
   ```
4. **Check Docker Desktop logs** for more details
5. **Use WSL2 backend** (not Hyper-V)

### Input Format Issues
If you encounter ffmpeg errors with exotic formats, convert to WAV first:

```bash
# Convert inside the container
docker run --rm -v "%cd%":/work ch-midi ffmpeg -i songs/input.mp3 -ar 44100 -ac 2 songs/input.wav
```

### Volume Mount Issues
- Use `%cd%` in Command Prompt or `${PWD}` in PowerShell
- Quote paths with spaces: `"songs/My Song.mp3"`
- Ensure Docker Desktop has access to your project directory

### Performance Tips
- **CPU-only**: No GPU acceleration needed (AMD GPU not required)
- **Memory**: Allocate 4-8 GB RAM in Docker Desktop settings
- **Processing time**: Expect 2-5 minutes for a 3-5 minute song

## Technical Details

### Dependencies
- **Base**: Python 3.10-slim
- **System**: ffmpeg, libsndfile1, git
- **Python**: Pinned versions for reproducibility
  - PyTorch 2.3.1+cpu (CPU-only wheels)
  - Demucs 4.0.0
  - Basic Pitch 0.3.0 with TensorFlow support
  - librosa, soundfile, mido

### Processing Pipeline
1. **Demucs**: Separates audio into stems (vocals, bass, drums, other)
2. **Basic Pitch**: Transcribes bass and selected lead stem to MIDI
3. **Output**: Creates individual MIDI files for each instrument

## Next Steps for Clone Hero

1. **Import MIDI files** into MIDI-CH Autocharter:
   - Download from: https://github.com/TheNathannator/MIDI-CH
   - Load your generated MIDI files
   - Configure difficulty levels and timing

2. **Refine in Moonscraper**:
   - Download from: https://github.com/Fireboyd78/Moonscraper
   - Import and adjust timing/notes
   - Fine-tune chart accuracy

3. **Use CAT in Reaper** for difficulty reductions and advanced processing

## Project Structure

```
autocharter/
├── Dockerfile                    # Working Docker image
├── pipeline.py                   # Working pipeline script
├── process_songs.bat             # Working batch file
├── README.md                     # This documentation
├── requirements.txt              # Dependencies
├── songs/                        # Your audio files
│   ├── G-DRAGON - TAKE ME (Official Audio).mp3
│   └── G-DRAGON - HOME SWEET HOME (Official Audio) (feat. TAEYANG & DAESUNG).mp3
├── out/                          # Generated MIDI files
│   ├── TAKE_ME_FINAL/
│   └── HOME_SWEET_HOME_FINAL/
├── separated/                    # Stem separation results
│   └── htdemucs/
└── charts/                       # Your Clone Hero charts
    ├── homesweethome/
    └── homesweethome-bass/
```

## Limitations

- **CPU-only**: No GPU acceleration (by design)
- **Offline only**: No web calls, fully self-contained
- **Deterministic**: Same inputs produce identical outputs
- **Processing time**: 2-5 minutes per song depending on length

## Support

For issues with:
- **Docker**: Check Docker Desktop WSL2 settings
- **Audio formats**: Convert to WAV first
- **Performance**: Increase Docker resource allocation
- **MIDI quality**: Basic Pitch provides robust transcription results

