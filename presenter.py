#!/usr/bin/env python3
"""
PDF Presenter - Synchronized dual-window PDF viewer for presentations.

Displays odd pages (1, 3, 5...) on the audience window and even pages (2, 4, 6...)
on the presenter window. Navigation in either window keeps both in sync.

Usage: python presenter.py presentation.pdf [config_file]

The optional config_file contains a comma-separated list of page numbers that
should be shown on the audience screen. All other pages become presenter notes.
Example config: 1,4,8 means slides 1,4,8 are for audience; pages 2,3 are notes
for slide 1, pages 5,6,7 are notes for slide 4, etc.

Copyright (C) 2025 Johannes Schaefer

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

This program incorporates PyMuPDF, which is available under the GNU Affero
General Public License v3. PyMuPDF is maintained by Artifex Software, Inc.
Copyright (C) Artifex Software, Inc.
For more information, visit: https://pymupdf.io/
"""

import sys
import signal
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF not installed. Run: pip install pymupdf")
    sys.exit(1)


def parse_config_file(config_path):
    """
    Parse a config file containing comma-separated page numbers for audience slides.
    
    Args:
        config_path: Path to the config file
        
    Returns:
        List of 1-indexed page numbers for audience slides, sorted ascending
    """
    path = Path(config_path)
    if not path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)
    
    try:
        content = path.read_text().strip()
        # Parse comma-separated integers
        pages = [int(p.strip()) for p in content.split(',') if p.strip()]
        
        if not pages:
            print("Error: Config file is empty or contains no valid page numbers")
            sys.exit(1)
        
        # Validate all pages are positive
        if any(p < 1 for p in pages):
            print("Error: Page numbers must be positive integers (1-indexed)")
            sys.exit(1)
        
        # Sort and remove duplicates
        pages = sorted(set(pages))
        return pages
        
    except ValueError as e:
        print(f"Error: Config file must contain comma-separated integers: {e}")
        sys.exit(1)


class PDFWindow:
    """A window displaying PDF pages with auto-scaling."""

    def __init__(self, master, title, on_navigate):
        self.window = tk.Toplevel(master) if master else tk.Tk()
        self.window.title(title)
        self.window.geometry("800x600")
        self.on_navigate = on_navigate
        self.is_fullscreen = False
        self.current_image = None

        # Canvas for PDF rendering
        self.canvas = tk.Canvas(self.window, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Bind navigation events to the window
        self.window.bind("<Right>", lambda e: self.on_navigate("next"))
        self.window.bind("<space>", lambda e: self.on_navigate("next"))
        self.window.bind("<Next>", lambda e: self.on_navigate("next"))      # Page Down
        self.window.bind("<Left>", lambda e: self.on_navigate("prev"))
        self.window.bind("<Prior>", lambda e: self.on_navigate("prev"))     # Page Up
        self.window.bind("<Home>", lambda e: self.on_navigate("first"))
        self.window.bind("<End>", lambda e: self.on_navigate("last"))
        self.window.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.window.bind("<Escape>", lambda e: self.exit_fullscreen())
        self.window.bind("<Configure>", self.on_resize)

    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        self.is_fullscreen = not self.is_fullscreen
        self.window.attributes("-fullscreen", self.is_fullscreen)

    def exit_fullscreen(self):
        """Exit fullscreen mode."""
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.window.attributes("-fullscreen", False)

    def on_resize(self, event):
        """Handle window resize - trigger redraw."""
        if hasattr(self, 'pending_resize'):
            self.window.after_cancel(self.pending_resize)
        self.pending_resize = self.window.after(100, lambda: self.on_navigate("refresh"))

    def display_page(self, pixmap, no_page_message="No page available"):
        """Display a rendered PDF page (as PyMuPDF Pixmap)."""
        if pixmap is None:
            self.canvas.delete("all")
            self.canvas.create_text(
                self.canvas.winfo_width() // 2,
                self.canvas.winfo_height() // 2,
                text=no_page_message,
                fill="white",
                font=("sans-serif", 24)
            )
            return

        # Get canvas dimensions
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()

        if canvas_w < 10 or canvas_h < 10:
            return

        # Convert pixmap to PhotoImage
        img_data = pixmap.tobytes("ppm")
        self.current_image = tk.PhotoImage(data=img_data)

        # Center on canvas
        self.canvas.delete("all")
        self.canvas.create_image(
            canvas_w // 2, canvas_h // 2,
            image=self.current_image,
            anchor=tk.CENTER
        )

    def set_title(self, title):
        """Update window title."""
        self.window.title(title)


class PDFPresenter:
    """Main presenter application managing two synchronized PDF windows."""

    def __init__(self, pdf_path, audience_pages=None):
        """
        Initialize the presenter.
        
        Args:
            pdf_path: Path to the PDF file
            audience_pages: Optional list of 1-indexed page numbers for audience slides.
                           If None, uses default behavior (odd pages for audience).
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            print(f"Error: File not found: {pdf_path}")
            sys.exit(1)

        # Load PDF
        try:
            self.doc = fitz.open(pdf_path)
        except Exception as e:
            print(f"Error opening PDF: {e}")
            sys.exit(1)

        self.total_pages = len(self.doc)
        
        # Build slide mapping based on config or default behavior
        self.slides = self._build_slide_mapping(audience_pages)
        self.num_slides = len(self.slides)
        self.current_slide = 0  # 0-indexed
        self.current_notes_index = 0  # 0-indexed index into presenter_pages for current slide

        if self.total_pages < 2:
            print("Warning: PDF has less than 2 pages. Presenter notes will be empty.")

        # Create root window (hidden)
        self.root = tk.Tk()
        self.root.withdraw()

        # Create viewer windows
        self.audience_window = PDFWindow(self.root, "Audience View", self.navigate)
        self.presenter_window = PDFWindow(self.root, "Presenter Notes", self.navigate)

        # Position windows side by side initially
        self.audience_window.window.geometry("800x600+50+50")
        self.presenter_window.window.geometry("800x600+900+50")

        # Handle window close
        self.audience_window.window.protocol("WM_DELETE_WINDOW", self.quit)
        self.presenter_window.window.protocol("WM_DELETE_WINDOW", self.quit)

        # Blank screen state
        self.is_blanked = False

        # Use bind_all on root to catch all key events regardless of focus
        # This is more reliable than per-widget bindings
        self.root.bind_all("<Key-b>", lambda e: self.toggle_blank())
        self.root.bind_all("<Key-B>", lambda e: self.toggle_blank())
        self.root.bind_all("<Key-h>", lambda e: self.show_help())
        self.root.bind_all("<Key-H>", lambda e: self.show_help())
        self.root.bind_all("<Key-x>", lambda e: self.quit())
        self.root.bind_all("<Key-X>", lambda e: self.quit())
        
        # Slide jump: digit input and Return key
        self.page_input = ""
        for digit in "0123456789":
            self.root.bind_all(f"<Key-{digit}>", self._on_digit)
        self.root.bind_all("<Return>", self._on_return)
        self.root.bind_all("<KP_Enter>", self._on_return)

        # Handle Ctrl+C (SIGINT) to exit gracefully
        # Use a more direct approach for immediate exit
        def handle_sigint(signum, frame):
            # Try to cleanup and exit immediately
            try:
                self.doc.close()
            except:
                pass
            # Destroy windows and exit
            try:
                self.root.quit()
                self.root.destroy()
            except:
                pass
            sys.exit(0)
        signal.signal(signal.SIGINT, handle_sigint)

        # Help window reference
        self.help_window = None

        # Initial display
        self.root.after(100, self.update_display)
    
    def _build_slide_mapping(self, audience_pages):
        """
        Build a mapping from slide index to (audience_page, presenter_pages).
        
        Args:
            audience_pages: List of 1-indexed page numbers for audience slides,
                           or None for default behavior.
        
        Returns:
            List of tuples: [(audience_page_0idx, [presenter_pages_0idx]), ...]
        """
        if audience_pages is None:
            # Default behavior: odd pages (1,3,5...) for audience, even (2,4,6...) for presenter
            slides = []
            for i in range(0, self.total_pages, 2):
                audience_page = i  # 0-indexed
                presenter_pages = [i + 1] if i + 1 < self.total_pages else []
                slides.append((audience_page, presenter_pages))
            return slides
        
        # Custom audience pages from config
        # Convert to 0-indexed and filter out pages beyond PDF length
        audience_pages_0idx = [p - 1 for p in audience_pages if p <= self.total_pages]
        
        if not audience_pages_0idx:
            print("Error: No valid audience pages found within PDF page range")
            sys.exit(1)
        
        slides = []
        for i, audience_page in enumerate(audience_pages_0idx):
            # Presenter pages are all pages between this audience page and the next
            if i + 1 < len(audience_pages_0idx):
                next_audience = audience_pages_0idx[i + 1]
            else:
                next_audience = self.total_pages
            
            presenter_pages = list(range(audience_page + 1, next_audience))
            slides.append((audience_page, presenter_pages))
        
        return slides

    def _on_digit(self, event):
        """Handle digit key input for slide number entry."""
        if event.char and event.char.isdigit():
            self.page_input += event.char

    def _on_return(self, event):
        """Handle Return/Enter key to jump to entered slide number."""
        if self.page_input:
            try:
                slide_num = int(self.page_input)
                self.navigate("goto", slide_num)
            except (ValueError, TypeError):
                pass  # Invalid input, ignore
            finally:
                self.page_input = ""

    def toggle_blank(self):
        """Toggle blank screen for audience window."""
        self.is_blanked = not self.is_blanked
        self.update_display()

    def show_help(self):
        """Show help window with key bindings."""
        # If help window already exists, bring it to front
        if self.help_window is not None and self.help_window.winfo_exists():
            self.help_window.lift()
            self.help_window.focus_set()
            return

        # Create help window
        self.help_window = tk.Toplevel(self.root)
        self.help_window.title("Keyboard Shortcuts")
        self.help_window.geometry("400x350")
        self.help_window.resizable(False, False)

        # Make it stay on top
        self.help_window.attributes("-topmost", True)

        # Help content
        help_text = """
  NAVIGATION
  ──────────────────────────────
  →  / Space / PgDn   Next slide
  ←  / PgUp           Previous slide
  Home                First slide
  End                 Last slide
  Number + Enter      Jump to slide

  DISPLAY
  ──────────────────────────────
  B               Blank audience screen
  F11             Toggle fullscreen
  Escape          Exit fullscreen

  OTHER
  ──────────────────────────────
  H               Show this help
  X               Quit application
  Close window    Quit application
  Ctrl+C          Quit application
"""

        # Create frame with padding
        frame = tk.Frame(self.help_window, bg="#2b2b2b", padx=20, pady=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # Help label
        label = tk.Label(
            frame,
            text=help_text,
            font=("monospace", 11),
            bg="#2b2b2b",
            fg="#e0e0e0",
            justify=tk.LEFT,
            anchor="nw"
        )
        label.pack(fill=tk.BOTH, expand=True)

        # Close button
        close_btn = tk.Button(
            frame,
            text="Close (Esc)",
            command=self.help_window.destroy,
            bg="#404040",
            fg="#e0e0e0",
            activebackground="#505050",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=15,
            pady=5
        )
        close_btn.pack(pady=(10, 0))

        # Bind Escape to close
        self.help_window.bind("<Escape>", lambda e: self.help_window.destroy())
        self.help_window.bind("<h>", lambda e: self.help_window.destroy())
        self.help_window.bind("<H>", lambda e: self.help_window.destroy())

    def navigate(self, action, value=None):
        """Handle navigation commands."""
        # Any navigation unblocks the screen
        if action != "refresh":
            self.is_blanked = False

        if action == "next":
            # Get current slide's presenter pages
            _, presenter_pages = self.slides[self.current_slide]
            # If there are notes and we haven't reached the last one, advance notes index
            if presenter_pages and self.current_notes_index < len(presenter_pages) - 1:
                self.current_notes_index += 1
            # Otherwise, advance to next slide
            elif self.current_slide < self.num_slides - 1:
                self.current_slide += 1
                self.current_notes_index = 0
        elif action == "prev":
            # If we're not at the first notes page, go back in notes
            if self.current_notes_index > 0:
                self.current_notes_index -= 1
            # Otherwise, go to previous slide
            elif self.current_slide > 0:
                self.current_slide -= 1
                # Set notes index to last notes page of previous slide (or 0 if no notes)
                _, presenter_pages = self.slides[self.current_slide]
                self.current_notes_index = len(presenter_pages) - 1 if presenter_pages else 0
        elif action == "first":
            self.current_slide = 0
            self.current_notes_index = 0
        elif action == "last":
            self.current_slide = self.num_slides - 1
            # Set notes index to last notes page of last slide (or 0 if no notes)
            _, presenter_pages = self.slides[self.current_slide]
            self.current_notes_index = len(presenter_pages) - 1 if presenter_pages else 0
        elif action == "goto" and value is not None:
            # User inputs 1-indexed slide number
            target = value - 1
            if 0 <= target < self.num_slides:
                self.current_slide = target
                self.current_notes_index = 0
        elif action == "refresh":
            pass  # Just redraw

        self.update_display()

    def render_page(self, page_num, canvas_width, canvas_height):
        """Render a PDF page scaled to fit the canvas."""
        if page_num < 0 or page_num >= self.total_pages:
            return None

        page = self.doc[page_num]
        page_rect = page.rect

        # Calculate scale to fit canvas while maintaining aspect ratio
        scale_x = canvas_width / page_rect.width
        scale_y = canvas_height / page_rect.height
        scale = min(scale_x, scale_y) * 0.95  # 95% to add small margin

        # Create transformation matrix
        mat = fitz.Matrix(scale, scale)

        # Render page
        pixmap = page.get_pixmap(matrix=mat, alpha=False)
        return pixmap

    def update_display(self):
        """Update both windows with current slide."""
        # Get page mapping for current slide
        audience_page, presenter_pages = self.slides[self.current_slide]

        # Ensure current_notes_index is valid
        if presenter_pages:
            self.current_notes_index = min(self.current_notes_index, len(presenter_pages) - 1)
        else:
            self.current_notes_index = 0

        # Render and display audience page
        aw = self.audience_window.canvas.winfo_width()
        ah = self.audience_window.canvas.winfo_height()
        if aw > 10 and ah > 10:
            if self.is_blanked:
                # Show black screen
                self.audience_window.canvas.delete("all")
                self.audience_window.current_image = None
            else:
                audience_pixmap = self.render_page(audience_page, aw, ah)
                self.audience_window.display_page(audience_pixmap)

        # Render and display presenter page based on current notes index
        pw = self.presenter_window.canvas.winfo_width()
        ph = self.presenter_window.canvas.winfo_height()
        if pw > 10 and ph > 10:
            if presenter_pages:
                # Show the notes page at current index
                presenter_page = presenter_pages[self.current_notes_index]
                presenter_pixmap = self.render_page(presenter_page, pw, ph)
                self.presenter_window.display_page(presenter_pixmap)
            else:
                # No notes available - show black screen with message
                self.presenter_window.display_page(None, "No related notes available")

        # Update window titles
        slide_info = f"Slide {self.current_slide + 1}/{self.num_slides}"
        notes_info = ""
        if presenter_pages:
            if len(presenter_pages) > 1:
                notes_info = f" (Notes {self.current_notes_index + 1}/{len(presenter_pages)})"
            else:
                notes_info = " (1 note)"
        blank_indicator = " [BLANKED]" if self.is_blanked else ""
        self.audience_window.set_title(f"Audience View - {slide_info}{blank_indicator}")
        self.presenter_window.set_title(f"Presenter Notes - {slide_info}{notes_info}{blank_indicator}")

    def quit(self):
        """Clean up and exit."""
        try:
            self.doc.close()
        except:
            pass  # Ignore errors during cleanup
        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def run(self):
        """Start the application."""
        print(f"Loaded: {self.pdf_path.name}")
        print(f"Total pages: {self.total_pages}, Slides: {self.num_slides}")
        
        # Show slide mapping summary
        print("\nSlide mapping:")
        for i, (aud_page, pres_pages) in enumerate(self.slides[:5]):  # Show first 5
            pres_str = f"notes: {[p+1 for p in pres_pages]}" if pres_pages else "no notes"
            print(f"  Slide {i+1}: page {aud_page+1} ({pres_str})")
        if len(self.slides) > 5:
            print(f"  ... and {len(self.slides) - 5} more slides")
        
        print("\nControls:")
        print("  Right/Space/PgDn      - Next slide")
        print("  Left/PgUp             - Previous slide")
        print("  Home                  - First slide")
        print("  End                   - Last slide")
        print("  B                     - Blank/unblank audience screen")
        print("  H                     - Show help (presenter window)")
        print("  F11                   - Toggle fullscreen")
        print("  Escape                - Exit fullscreen")
        print("  Number+Enter          - Go to slide number")
        print("  X                     - Quit application")
        print("  Ctrl+C (in terminal)  - Quit application")
        print("\nDrag 'Audience View' to projector, press F11 for fullscreen.")

        self.root.mainloop()


def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python presenter.py <pdf_file> [config_file]")
        print("\nDefault behavior (no config file):")
        print("  - Odd pages (1, 3, 5...): Audience slides")
        print("  - Even pages (2, 4, 6...): Presenter notes")
        print("\nWith config file:")
        print("  The config file should contain a comma-separated list of page numbers")
        print("  that are meant for the audience screen. All other pages become presenter notes.")
        print("\n  Example config content: 1,4,8")
        print("  - Page 1 is audience slide 1, pages 2-3 are its presenter notes")
        print("  - Page 4 is audience slide 2, pages 5-7 are its presenter notes")
        print("  - Page 8 is audience slide 3, remaining pages are its notes")
        sys.exit(1)

    pdf_path = sys.argv[1]
    
    audience_pages = None
    if len(sys.argv) == 3:
        config_path = sys.argv[2]
        audience_pages = parse_config_file(config_path)
        print(f"Config loaded: audience pages are {audience_pages}")
    
    presenter = PDFPresenter(pdf_path, audience_pages)
    presenter.run()


if __name__ == "__main__":
    main()

