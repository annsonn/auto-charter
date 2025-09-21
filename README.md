# Autocharter: Audio ? MIDI ? Clone Hero Charts

This project builds a Windows-friendly, Dockerized toolchain for turning songs into playable Clone Hero charts. It wraps Demucs, Spotify Basic Pitch, ffmpeg/Opus, and the MIDI-CH auto-charter into a repeatable pipeline.

## Prerequisites
- Windows 10/11 with [Docker Desktop](https://www.docker.com/products/docker-desktop) + WSL 2 backend
- At least 4 vCPUs and 6–8?GB RAM allocated to Docker Desktop
- PowerShell (ships with Windows)
- Git (optional, but recommended)

## Quick Start (one command)
1. Clone or download this repo and open a PowerShell window in the project root.
2. Drop MP3/WAV files into `songs/`.
3. Run:
   ```powershell
   .\run_all.bat
   ```

`run_all.bat` orchestrates the full workflow:
- Rebuilds the `ch-midi` image and runs `process_songs.bat` to create stems and MIDIs for every file in `songs/`.
- Rebuilds the `ffmpeg-opus` image and runs `convert_opus.bat` to generate `opus-output/<Song>.opus` alongside the MIDIs.
- Rebuilds the `midi-ch-batch` image and runs `auto-chart.bat` to feed each `merged.mid` to MIDI-CH, copy `notes.mid`, and stage a chart folder (with matching `song.opus`) in `charts/`.

When the script finishes, inspect the results under:
- `out/<Song>/` – individual MIDIs (`bass`, `vocals/other`, `merged.mid`, `notes.mid`)
- `opus-output/<Song>.opus` – Opus-transcoded audio for Clone Hero packages
- `charts/<Song>/` – starter Clone Hero folder containing `notes.chart`, `notes.mid`, `song.opus`, and auto-generated `song.ini`

## Running stages individually
Use these scripts if you prefer more control:

| Stage | Command | Purpose |
| --- | --- | --- |
| Stem separation + MIDIs | `.\process_songs.bat` | Runs Demucs + Basic Pitch. Accepts optional file arguments. |
| Audio transcode | `.\convert_opus.bat` | Converts MP3s to Opus (`opus-output/`). |
| Auto-chart | `.\auto-chart.bat` | Downloads MIDI-CH, processes every `merged.mid`, copies `notes.mid` + `song.opus`, writes chart folders. |

Each script rebuilds its Docker image before running so changes to Dockerfiles are always picked up. Pass `--help` to `auto-chart.bat` for advanced flags (custom input/output/image names).

## Manual Docker invocation (advanced)
If you hit issues with the batch scripts, you can run the underlying containers manually:

```powershell
# Process a single song
docker run --rm -v "${PWD}:/work" ch-midi \
  python /usr/local/bin/pipeline.py "songs/My Song.mp3" --out out

# Convert a song to Opus
docker run --rm -v "${PWD}:/work" ffmpeg-opus \
  -y -i "/work/songs/My Song.mp3" -c:a libopus -b:a 160k "/work/opus-output/My Song.opus"

# Auto-chart a specific folder
docker run --rm -v "${PWD}:/work" midi-ch-batch \
  --input /work/out --output /work/charts --opus /work/opus-output
```

## Project structure
```
autocharter/
+- Dockerfile              # ch-midi image (Demucs + Basic Pitch)
+- Dockerfile.midi-ch      # MIDI-CH automation image
+- Dockerfile.opus         # ffmpeg/libopus image
+- process_songs.bat       # Stage 1 driver
+- convert_opus.bat        # Stage 2 driver
+- auto-chart.bat          # Stage 3 driver
+- run_all.bat             # Runs all stages in order
+- tools/
¦   +- auto_chart_batch.js # Puppeteer automation for MIDI-CH
¦   +- convert_opus.ps1    # PowerShell helper for Opus batch
+- songs/                  # Place input MP3/WAV files here
+- out/                    # Generated MIDIs (created by Stage 1)
+- opus-output/            # Generated Opus files (Stage 2)
+- charts/                 # Clone Hero chart folders (Stage 3)
```

## Troubleshooting
- **Docker build fails**: Restart Docker Desktop, allocate more memory, or run `docker build --memory=4g -t ch-midi .`
- **Demucs errors / odd stems**: Try a different model via `process_songs.bat` arguments, or preprocess audio manually.
- **MIDI-CH ambiguity**: Inspect the generated folder in `charts/<Song>/`, adjust `song.ini`, and refine the chart in Moonscraper.
- **Opus not copied**: Ensure `convert_opus.bat` ran before `auto-chart.bat`; the latter pulls from `opus-output/` when available.

For a deep dive into each stage, see `docs/workflow.md`.
