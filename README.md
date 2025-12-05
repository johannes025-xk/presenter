# PDF Presenter

A simple synchronized dual-window PDF viewer for presentations on Linux.

Displays a single PDF with:
- **Odd pages (1, 3, 5...)** → Audience window (projector/external display)
- **Even pages (2, 4, 6...)** → Presenter window (your laptop screen)

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

```bash
python presenter.py your_presentation.pdf
```

## Preparing Your PDF

Create your PDF with interleaved pages:

| Page | Content |
|------|---------|
| 1 | Slide 1 (audience sees this) |
| 2 | Notes for slide 1 (you see this) |
| 3 | Slide 2 (audience sees this) |
| 4 | Notes for slide 2 (you see this) |
| 5 | Slide 2 (audience sees this again) |
| 6 | Another Notes-slide for slide 2 (you see this) |
| ... | ... |

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

1. Run `python presenter.py presentation.pdf`
2. Drag the "Audience View" window to your projector/external display
3. Press `F11` to make the audience window fullscreen
4. Keep "Presenter Notes" on your laptop screen
5. Navigate using keyboard from either window

## Requirements

- Python 3.6+
- Tkinter (included with Python on most Linux distributions)
- PyMuPDF (`pymupdf`)

