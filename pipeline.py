#!/usr/bin/env python3
"""
Working Audio to MIDI Pipeline for Clone Hero Charting
This version uses Basic Pitch correctly and handles the separated stems.
"""

import argparse
import os
import sys
import subprocess
import glob
from pathlib import Path
import logging

# For MIDI merging
import mido

def merge_midi_tracks(output_dir, part_map=None, merged_name="merged.mid"):
    """Merge MIDI files in output_dir into a multi-track MIDI file with named tracks."""
    if part_map is None:
        part_map = {
            "bass": "PART BASS",
            "vocals": "PART GUITAR",
            "other": "PART RHYTHM",
            "drums": "PART DRUMS"
        }
    output_dir = Path(output_dir)
    midis = []
    for part, track_name in part_map.items():
        part_dir = output_dir / part
        if not part_dir.exists():
            continue
        midi_files = list(part_dir.glob("*.mid"))
        if not midi_files:
            continue
        midi = mido.MidiFile(midi_files[0])
        # Rename the first track to the desired name
        if midi.tracks:
            midi.tracks[0].name = track_name
        midis.append((track_name, midi))
    if not midis:
        logger.warning(f"No MIDI files found to merge in {output_dir}")
        return False
    # Create a new multi-track MIDI file
    merged = mido.MidiFile()
    # Preserve PPQ from the first MIDI
    merged.ticks_per_beat = midis[0][1].ticks_per_beat
    for track_name, midi in midis:
        # Use only the first track from each file and ensure canonical track name meta
        track = midi.tracks[0].copy()
        # Insert a track_name meta message at the start (time 0)
        track.insert(0, mido.MetaMessage('track_name', name=track_name, time=0))
        merged.tracks.append(track)
    merged_path = output_dir / merged_name
    merged.save(merged_path)
    logger.info(f"Merged MIDI saved to {merged_path}")
    return True

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(cmd, cwd=None):
    """Run a command and return success status."""
    try:
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
        if result.stdout:
            logger.info(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        if e.stderr:
            logger.error(f"Error: {e.stderr.strip()}")
        return False

def run_demucs(audio_path, model="htdemucs"):
    """Run Demucs stem separation."""
    logger.info(f"Running Demucs stem separation with model {model}")
    
    cmd = ["python", "-m", "demucs.separate", "-n", model, audio_path]
    return run_command(cmd)

def run_basic_pitch(input_wav, output_dir):
    """Run Basic Pitch transcription using the correct command."""
    logger.info(f"Running Basic Pitch on {input_wav}")
    
    # Basic Pitch command format: basic-pitch output_dir input.wav
    cmd = ["basic-pitch", output_dir, input_wav]
    
    if not run_command(cmd):
        logger.error(f"Basic Pitch failed on {input_wav}")
        return False
    
    # Find the generated MIDI file
    output_path = Path(output_dir)
    midi_files = list(output_path.glob("*.mid"))
    
    if midi_files:
        logger.info(f"Basic Pitch output: {midi_files[0]}")
        return True
    else:
        logger.error(f"No MIDI output found in {output_dir}")
        return False

def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://") or s.startswith("www.")

def run_yt_dlp(url: str, out_base: str = "songs/tmp_download"):
    """Download audio from a URL via yt-dlp and return the resulting audio filepath."""
    logger.info(f"Downloading audio via yt-dlp: {url}")
    Path("songs").mkdir(exist_ok=True)
    cmd = [
        "yt-dlp",
        "-x",
        "--audio-format", "wav",
        "--force-overwrites",
        "-o", f"{out_base}.%(ext)s",
        url,
    ]
    if not run_command(cmd):
        logger.error("yt-dlp download failed")
        return None
    wav_path = Path(f"{out_base}.wav")
    if wav_path.exists():
        return str(wav_path)
    mp3_path = Path(f"{out_base}.mp3")
    if mp3_path.exists():
        return str(mp3_path)
    logger.error("yt-dlp did not produce expected audio file")
    return None

def find_demucs_output(audio_path, model="htdemucs"):
    """Find the Demucs output directory."""
    audio_name = Path(audio_path).stem
    separated_dir = Path("separated") / model / audio_name
    
    if not separated_dir.exists():
        logger.error(f"Demucs output not found at {separated_dir}")
        return None
    
    logger.info(f"Found Demucs output at {separated_dir}")
    return separated_dir

def main():
    parser = argparse.ArgumentParser(description="Working Audio to MIDI Pipeline")
    parser.add_argument("audio", help="Path to input MP3/WAV file")
    parser.add_argument("--model", default="htdemucs", help="Demucs model (default: htdemucs)")
    parser.add_argument("--out", default="out", help="Output directory (default: out)")
    parser.add_argument("--lead", choices=["vocals", "other"], default="vocals", 
                       help="Lead stem for transcription (default: vocals)")
    parser.add_argument("--drums", choices=["skip", "basic"], default="skip",
                       help="Drums transcription mode (default: skip)")
    
    args = parser.parse_args()
    
    # If a URL is provided, download audio to songs/tmp_download.wav (or .mp3)
    if is_url(args.audio):
        downloaded = run_yt_dlp(args.audio, out_base="songs/tmp_download")
        if not downloaded:
            logger.error("Failed to download audio from URL")
            sys.exit(1)
        args.audio = downloaded

    # Validate input file
    if not os.path.exists(args.audio):
        logger.error(f"Input file not found: {args.audio}")
        sys.exit(1)
    
    # Create output directory
    audio_name = Path(args.audio).stem
    output_dir = Path(args.out) / audio_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Processing {args.audio} -> {output_dir}")
    
    # Step 1: Run Demucs stem separation
    if not run_demucs(args.audio, args.model):
        logger.error("Demucs separation failed")
        sys.exit(1)
    
    # Step 2: Find Demucs output
    demucs_output = find_demucs_output(args.audio, args.model)
    if not demucs_output:
        logger.error("Could not find Demucs output")
        sys.exit(1)
    
    # Step 3: Run Basic Pitch on bass
    bass_wav = demucs_output / "bass.wav"
    if bass_wav.exists():
        bass_output_dir = output_dir / "bass"
        bass_output_dir.mkdir(exist_ok=True)
        if not run_basic_pitch(str(bass_wav), str(bass_output_dir)):
            logger.warning("Bass transcription failed")
    else:
        logger.warning("Bass stem not found, skipping")
    

    # Step 4: Optional: Run Basic Pitch on drums (disabled by default)
    drums_wav = demucs_output / "drums.wav"
    if args.drums != "skip":
        if drums_wav.exists():
            drums_output_dir = output_dir / "drums"
            drums_output_dir.mkdir(exist_ok=True)
            if not run_basic_pitch(str(drums_wav), str(drums_output_dir)):
                logger.warning("Drums transcription failed")
        else:
            logger.warning("Drums stem not found, skipping")
    else:
        logger.info("Skipping drums transcription (use --drums basic to enable)")

    # Step 5: Run Basic Pitch on lead stem
    lead_wav = demucs_output / f"{args.lead}.wav"
    if lead_wav.exists():
        lead_output_dir = output_dir / args.lead
        lead_output_dir.mkdir(exist_ok=True)
        if not run_basic_pitch(str(lead_wav), str(lead_output_dir)):
            logger.warning(f"{args.lead} transcription failed")
    else:
        logger.warning(f"{args.lead} stem not found, skipping")
    


    # Step 6: Merge MIDI files into a multi-track MIDI with canonical PART names
    if args.lead == "vocals":
        part_map = {"vocals": "PART GUITAR", "bass": "PART BASS", "other": "PART RHYTHM"}
    else:
        part_map = {"other": "PART GUITAR", "bass": "PART BASS", "vocals": "PART RHYTHM"}
    # Only include drums in mapping if a drums MIDI was actually generated
    drums_dir = (output_dir / "drums")
    if drums_dir.exists() and list(drums_dir.glob("*.mid")):
        part_map["drums"] = "PART DRUMS"
    merge_midi_tracks(output_dir, part_map=part_map)

    logger.info("Pipeline completed successfully!")
    logger.info(f"Output files in: {output_dir}")

if __name__ == "__main__":
    main()
