# TMC-FPV Auto Editor

*The Lazy Persons DVR Editor — Vibe Coded With Blind Ignorance*

An experimental video editor built for FPV pilots. Give it your footage, choose how you want it edited, add music, and let it do the hard work.

TMC-FPV Auto Editor is designed to turn DVR footage into a finished video without spending hours manually selecting clips and cutting footage.

---

## 🚧 Community Beta

This is experimental software under active development. Features, editing behaviour and results may change between builds.

The community beta is provided for testing, experimentation and feedback. It isn't a finished commercial product, and automated editing won't always make the choices you would make yourself.

**Keep your original footage and always review the finished video.**

---

# Download & Installation

## Download

Visit the [Latest Release](../../releases/latest) page and download the standalone ZIP file.

**Download the Standalone ZIP — not the GitHub Source Code archives.**

The Source Code downloads are for the software's source files and are not the ready-to-run application.

## Extract

1. Locate the downloaded ZIP file.
2. Right-click it and select **Extract All**.
3. Extract it to a folder of your choice.

Don't run the application directly from inside the ZIP file.

## Launch

Open the extracted folder and run **TMC-FPV Auto Editor**.

The standalone application does not require you to install Python.

### Windows Security Warning

Because the community beta is an unsigned application, Windows may display a security warning when you first launch it.

Only download the application from the official TMC-FPV Auto Editor GitHub repository.

---

# Using the Editor

The editor is arranged into three stages, followed by the generation and rendering controls.

## Stage 1 — Download / Import Footage (Optional)

Stage 1 allows you to download footage before editing. You can skip this stage entirely if your DVR footage is already on your computer.

### Source

Choose the source you want to use for downloading footage.

The interface currently provides options for downloading from YouTube and working with Google Photos shared links.

### Video / Playlist / Channel / Shared Album URL

Paste the appropriate link into this field.

Depending on the selected source, this may be a video, playlist, channel or shared album URL.

### Download Quality

Select the desired download quality from the dropdown.

This determines the quality of the downloaded video where the selected source supports quality selection.

### Destination

Select the destination folder for downloaded footage.

**Select the destination folder before starting a download.**

### Download

Use the **DOWNLOAD** button to start downloading from the selected source.

The interface notes that YouTube downloads use yt-dlp, video-only downloads are used where available, quality is selectable, and archive handling can skip repeats.

### Open Google Photos Link

Google Photos shared albums are handled differently.

Use **OPEN GOOGLE PHOTOS LINK** to open the shared album in your browser. From there, use Google Photos' own download option to download the album.

If the album downloads as a ZIP file, extract it into your selected footage destination folder before proceeding.

---

## Stage 2 — Project Folders

Stage 2 is where you tell the editor where your footage, music and finished video are located.

### Footage Folder

Select the folder containing your source DVR footage.

The editor uses the footage in this folder as the source material for your edit.

If you are working with recordings split across multiple files, place the relevant footage together in the folder you intend to use.

### Music File

Select the music file you want to use for your finished video.

The selected music determines the intended duration of the edit. The editor builds the video around the music rather than requiring you to specify a separate video duration.

Music also influences the editing process when using music-aware features.

### Output MP4

Choose where your finished video will be saved and specify the output MP4 file.

Make sure the destination has sufficient free space for the rendered video.

---

# Stage 3 — Edit Settings

Stage 3 contains the controls that determine how the video is assembled, the output format, and the visual effects.

## Editing Style / Clip Lengths

### Editing Style

Select the editing style you want to use.

The available styles influence the approach used when selecting and assembling clips. The selected style can affect the pacing and feel of the finished video.

### Minimum Clip (s)

Sets the minimum permitted clip duration in seconds.

This helps control how short individual sections of footage can be in the finished edit.

### Maximum Clip (s)

Sets the maximum permitted clip duration in seconds.

This limits how long an individual selected section can run before another cut is introduced.

The minimum and maximum clip lengths can be adjusted to suit the footage and the style of edit you're trying to achieve.

---

## Quick Preset

Quick Presets allow you to quickly apply a predefined combination of editing settings rather than manually adjusting everything individually.

Select a preset from the dropdown and click **Apply**.

The preset will configure the relevant editing parameters for you. You can then adjust individual settings if you want to customise the result.

The preset dropdown can be used as a starting point rather than a restriction on your editing choices.

---

## Source Order (All Videos)

This setting determines how source footage is ordered during the editing process.

### Random

Randomises the source order, allowing footage to be selected without following the original flight sequence.

This is useful when you want a varied edit or don't necessarily want the video to follow the flight chronologically.

### Chronological

Uses the source footage in chronological order.

This is useful for long-range flights, journeys and recordings split across multiple files when you want the finished video to retain the progression of the flight.

---

# Output Settings

These controls determine the technical properties of your rendered video.

### Output Size

Select the output video resolution.

This determines the resolution at which your finished video is rendered.

### Quality

Select the output quality setting.

The available options control the encoding quality and affect the resulting file size and rendering requirements.

### Frame Rate

Select the frame rate for the finished video.

This determines how many frames per second the output video will contain.

### Vertical Footage

Choose how vertical footage is handled.

The available setting shown as **Original (fit)** allows the original vertical footage to be fitted into the output rather than automatically forcing it into a different crop.

### Aspect Ratio

Choose the aspect ratio of the finished video.

This allows you to choose the format appropriate for your intended use, such as widescreen video.

Consider your footage and intended platform when choosing output settings.

---

# Effects & Transitions

These options control some of the visual treatment applied during editing.

### Retro Handheld / Camcorder Look

Enable this option to apply the retro handheld/camcorder visual look to the finished video.

Leave it unchecked if you want your footage to retain its normal appearance.

### Fade Video In

Enables a fade-in effect at the beginning of the video.

### Fade Video Out

Enables a fade-out effect at the end of the video.

### Random Transitions

Enable this option to introduce random transitions between selected clips.

Leave it unchecked if you prefer cuts without randomly selected transition effects.

### Transition Strength

Controls the strength of the transitions used by the editor.

The available settings allow you to adjust how pronounced the transition effects are.

---

# Intro / Logo (Optional)

The editor allows you to add an optional intro or logo to the beginning of your finished video.

### Use Intro / Logo

Enable this checkbox to use an intro or logo.

### Intro / Logo File

Use the file selection button to choose the image you want to use.

### Intro Duration (Still Image)

Sets how long a still-image intro is displayed.

The duration is specified in seconds.

### Random Seed

The random seed allows you to control the random selection process.

Using the same seed with the same source material and settings can be useful when comparing edits or attempting to reproduce a particular selection.

### Copy Seed

Use **COPY SEED** to copy the seed value for reuse.

This is useful when you want to retain or share the seed used for a particular edit.

---

# Generating Your Video

Once your footage, music and settings are configured, you're ready to generate your video.

## Generate Video

Click **GENERATE VIDEO** to begin creating your edit using the current project settings.

The editor will process the source footage, select clips, assemble the video and render the output using your chosen settings.

Rendering time will depend on the source footage, output settings and your computer's performance.

## Generate Again

Use **GENERATE AGAIN** to generate another edit.

This is useful if you want to try another variation using your existing project setup rather than starting over.

Depending on your settings, the result may differ from your previous generation.

## Cancel Render

Use **CANCEL RENDER** to stop an active rendering process.

Rendering can take time, particularly with large amounts of source footage or higher output settings.

---

# Project & Output Controls

### Scan / Update Footage Library

Use **SCAN / UPDATE FOOTAGE LIBRARY** to scan or update the footage library used by the editor.

This is useful after adding, changing or replacing footage in your source folders.

### Cancel Scan

Use **CANCEL SCAN** to stop an active footage scan.

### Check Project

Use **CHECK PROJECT** to check the current project.

This is useful for checking your project setup before generating a video.

### Open Output Folder

Use **OPEN OUTPUT FOLDER** to open the location where your rendered video is saved.

### Play Finished Video

Use **PLAY FINISHED VIDEO** to play the completed output.

### Copy Log / Error Details

Use **COPY LOG / ERROR DETAILS** to copy the diagnostic information from the editor.

If you're reporting a bug or unexpected behaviour, this information may be useful when submitting a report.

---

# Status, Render Estimates & Logs

The editor displays status information near the bottom of the interface.

This can include:

- Estimated rendering time
- Number of source files detected
- Available free disk space
- Application status
- Progress information
- Processing and rendering messages
- Error and diagnostic information

The estimated rendering time is only a rough guide and actual processing time may vary.

If something appears to have gone wrong, check the log area at the bottom of the application. If reporting an issue, use **COPY LOG / ERROR DETAILS** to include diagnostic information.

---

# Tips for Better Results

- Make sure your footage folder contains the recordings you actually want to use.
- Try different editing styles and quick presets.
- Experiment with minimum and maximum clip lengths.
- Use chronological source order when preserving the progression of a flight is important.
- Try random source order when you want a more varied edit.
- Choose music that suits the footage.
- Experiment with transitions rather than automatically assuming more effects are better.
- Review the finished video before uploading.
- Keep your original recordings.

The editor is designed to do the heavy lifting, but it doesn't know which moments of your flight are personally important to you.

---

# Feedback & Bug Reports

This is a community beta, and feedback is an important part of its development.

If you encounter bugs, crashes, unexpected behaviour, editing problems or have ideas for improvements, please report them through the repository's **Issues** section.

When reporting an issue, include as much information as possible:

- Editor version
- Editing style selected
- Quick preset used
- Source order
- Output settings
- Whether music was used
- What you expected to happen
- What actually happened
- Screenshots where useful

If the problem involves an error or unexpected behaviour, please use **COPY LOG / ERROR DETAILS** and include the copied information with your report.

Constructive feedback, real examples and testing with different types of FPV footage are extremely useful.

---

# Disclaimer

TMC-FPV Auto Editor is experimental software supplied for community testing.

Features and behaviour may change between releases. The editor may produce unexpected results, and automated clip selection or transitions will not always be perfect.

Always retain your original footage and review your finished video before publishing or sharing it.

---

*Spend on fun, not on kit.*

**TMC-FPV**
