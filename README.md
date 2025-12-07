# PDF Presenter

A simple synchronized dual-window PDF viewer for presentations on Linux.

By default, displays a single PDF with:
- **Odd pages (1, 3, 5...)** → Audience window (projector/external display)
- **Even pages (2, 4, 6...)** → Presenter window (your laptop screen)

You can also use a **config file** to specify custom page mappings, allowing multiple presenter slides per audience slide.

Both windows stay in sync—navigate from either one.

## Installation

```bash
# Install tkinter (system package, required on most Linux distros)
# Debian/Ubuntu:
sudo apt install python3-tk

# Fedora/RHEL:
sudo dnf install python3-tkinter

# Arch:
sudo pacman -S tk

# Install Python dependency
pip install -r requirements.txt
```

## Usage

**Basic usage (default behavior):**
```bash
python presenter.py your_presentation.pdf
```

**With custom page mapping (config file):**
```bash
python presenter.py your_presentation.pdf config.txt
```

The config file allows you to specify which pages are shown to the audience, with all other pages becoming presenter notes. This is useful when you have multiple presenter slides for a single audience slide.

## Preparing Your PDF

### Default Behavior (No Config File)

By default, the presenter expects interleaved pages where odd pages are for the audience and even pages are presenter notes:

| Page | Content |
|------|---------|
| 1 | Slide 1 (audience sees this) |
| 2 | Notes for slide 1 (you see this) |
| 3 | Slide 2 (audience sees this) |
| 4 | Notes for slide 2 (you see this) |
| 5 | Slide 3 (audience sees this) |
| 6 | Notes for slide 3 (you see this) |
| ... | ... |

### Custom Page Mapping (With Config File)

If you have multiple presenter slides for one audience slide, or a non-standard page layout, you can use a config file to specify which pages are for the audience.

**Example:** Config file `config.txt` containing `1,4,8`

This means:
- **Slide 1**: Page 1 (audience), pages 2-3 (presenter notes)
- **Slide 2**: Page 4 (audience), pages 5-7 (presenter notes)
- **Slide 3**: Page 8 (audience), remaining pages (presenter notes)

**Config file format:**
- Create a text file with comma-separated page numbers
- Page numbers are 1-indexed (first page is 1, not 0)
- Numbers are automatically sorted and duplicates removed
- Example: `1,4,8` or `1, 4, 8` (spaces are optional)

**When to use a config file:**
- You have more than one presenter slide per audience slide
- Your PDF doesn't follow the standard odd/even pattern
- You want to skip certain pages from the audience view
- You have a custom page layout that doesn't fit the default pattern

### Tips for creating interleaved PDFs

**PowerPoint/LibreOffice:**
1. Export slides as PDF
2. Export notes/backup slides as separate PDF
3. Use `pdftk` to interleave:
   ```bash
   pdftk A=slides.pdf B=notes.pdf shuffle A B output presentation.pdf
   ```

**LaTeX Beamer:**
Use the `\note{}` command with `show notes on second screen` option.

## Config File Examples

### Example 1: Default Behavior Equivalent

If you want to explicitly use the default behavior, create `config.txt`:
```
1,3,5,7,9
```

This is equivalent to not using a config file at all (odd pages for audience, even pages for presenter).

### Example 2: Multiple Presenter Slides

Config file `config.txt`:
```
1,4,8
```

**Resulting slide mapping:**
- **Slide 1**: Page 1 (audience) → Pages 2-3 (presenter notes)
- **Slide 2**: Page 4 (audience) → Pages 5-7 (presenter notes)
- **Slide 3**: Page 8 (audience) → Pages 9+ (presenter notes)

This allows you to have 2 or more presenter slides for each audience slide.

### Example 3: Custom Layout

Config file `config.txt`:
```
1,5,12,20
```

**Resulting slide mapping:**
- **Slide 1**: Page 1 (audience) → Pages 2-4 (presenter notes)
- **Slide 2**: Page 5 (audience) → Pages 6-11 (presenter notes)
- **Slide 3**: Page 12 (audience) → Pages 13-19 (presenter notes)
- **Slide 4**: Page 20 (audience) → Remaining pages (presenter notes)

### Creating a Config File

1. Create a text file (e.g., `config.txt`)
2. List the page numbers for audience slides, separated by commas
3. Save the file
4. Run: `python presenter.py presentation.pdf config.txt`

**Note:** The application will show you the slide mapping when it starts, so you can verify your config file is correct.

## Controls

| Key | Action |
|-----|--------|
| `→` / `Space` / `Page Down` | Next slide |
| `←` / `Page Up` | Previous slide |
| `Home` | First slide |
| `End` | Last slide |
| `B` | Blank audience screen (press again or navigate to restore) |
| `H` | Show help window (presenter window only) |
| `F11` | Toggle fullscreen (audience window) |
| `Escape` | Exit fullscreen |
| `Number` + `Enter` | Jump to slide number |

**USB Presenter Support:** Most handheld presenter devices (Logitech, Kensington, etc.) work out of the box as they send Page Down/Page Up or arrow keys.

## Presentation Setup

1. Run `python presenter.py presentation.pdf` (or with config file: `python presenter.py presentation.pdf config.txt`)
2. Drag the "Audience View" window to your projector/external display
3. Press `F11` to make the audience window fullscreen
4. Keep "Presenter Notes" on your laptop screen
5. Navigate using keyboard from either window

## Requirements

- Python 3.6+
- Tkinter (included with Python on most Linux distributions)
- PyMuPDF (`pymupdf`)

## License

Copyright (C) 2025 Johannes Schaefer

This project is licensed under the GNU Affero General Public License v3 (AGPL-3.0).

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

### Third-Party Components

This project incorporates **PyMuPDF**, which is available under the GNU Affero General Public License v3. PyMuPDF is maintained by Artifex Software, Inc. Copyright (C) Artifex Software, Inc. For more information, visit: https://pymupdf.io/

### Source Code

The complete source code for this project is available in this repository. Under the terms of the AGPL v3, if you distribute or make this software available over a network, you must provide access to the corresponding source code.

See the [LICENSE](LICENSE) file for the full license text.

