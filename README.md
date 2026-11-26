# TMC-FPV AutoEditor v19.6.7

A music-led FPV video editing tool with a Director Engine, Audio Brain, FPV interpretation, and a pre-render Storyboard review gate.


## Included files
- `TMC-FPV AutoEditor v19.6.7.py` — application source
- `tmc_audio_brain.py` — companion audio analysis module (required by the main app)
- `.github/workflows/release-windows.yml` — GitHub Actions workflow to build a Windows executable and publish a GitHub Release when a `v19.6.7` tag is pushed


## Release/build
1. Upload this repository to GitHub.
2. Create and push the tag `v19.6.7` (or run the workflow manually from Actions).
3. The workflow builds a Windows one-file GUI executable with PyInstaller and publishes the executable plus source files and source ZIP to the GitHub Release.


## Runtime notes
- The app downloads/verifies its portable FFmpeg and yt-dlp dependencies when needed.
- Hardware encoding is disabled in the Work Edition; CPU fallback is used.
- Python syntax and source-package integrity have been checked locally. Windows GUI operation, preview playback on user footage, and a complete render are not independently validated here.


## v19.6.7 feature freeze notes
- Mandatory Storyboard approval gate; collapsing/hiding the Storyboard does not approve or start rendering.
- Source-frame thumbnails populated from the original footage.
- Clip replacement refreshes the thumbnail and selected-shot preview.
- Larger Storyboard thumbnails and left/right arrow selection navigation.
- Storyboard dark/light theme follows the application theme.
- Selected-clip preview uses up to 1.5 seconds of pre-roll, then the planned segment.
- Preview scaling forces even dimensions for H.264 compatibility with portrait footage.
- Director music-led arcs, source diversity, visual-pattern repetition awareness, WOW moments, and explainable decisions.
- Audio Brain music structure interpretation; beats provide edit opportunities rather than mandatory cuts.
- Turn It Up To Eleven intensifies the edit without rerolling the selected moments/music structure.


## Limitations
- Storyboard thumbnails populate at the final plan/review handoff; live incremental population during the Director's internal clip-selection loop is not implemented.
- Seed-based repeatability depends on identical inputs, settings, source ordering, and code version; it is not guaranteed across changed environments or code.
