#!/usr/bin/env python3
"""
PDF Presenter - Synchronized dual-window PDF viewer for presentations.

Displays odd pages (1, 3, 5...) on the audience window and even pages (2, 4, 6...)
on the presenter window. Navigation in either window keeps both in sync.

Usage: python presenter.py presentation.pdf
"""

import sys
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF not installed. Run: pip install pymupdf")
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

        # Bind events
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

        # Page number display with key bindings
        self.window.bind("<Key>", self.on_key)
        self.page_input = ""

    def on_key(self, event):
        """Handle number key input for direct page navigation."""
        if event.char.isdigit():
            self.page_input += event.char
        elif event.keysym == "Return" and self.page_input:
            self.on_navigate("goto", int(self.page_input))
            self.page_input = ""
        elif event.keysym not in ("Right", "Left", "space", "Home", "End", "F11", "Escape"):
            self.page_input = ""

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

    def display_page(self, pixmap):
        """Display a rendered PDF page (as PyMuPDF Pixmap)."""
        if pixmap is None:
            self.canvas.delete("all")
            self.canvas.create_text(
                self.canvas.winfo_width() // 2,
                self.canvas.winfo_height() // 2,
                text="No page available",
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

    def __init__(self, pdf_path):
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

        # Calculate number of slides (pairs of pages)
        self.total_pages = len(self.doc)
        self.num_slides = (self.total_pages + 1) // 2  # Round up for odd page count
        self.current_slide = 0  # 0-indexed

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

        # Bind 'b' key for blank screen on both windows
        self.audience_window.window.bind("<b>", lambda e: self.toggle_blank())
        self.audience_window.window.bind("<B>", lambda e: self.toggle_blank())
        self.presenter_window.window.bind("<b>", lambda e: self.toggle_blank())
        self.presenter_window.window.bind("<B>", lambda e: self.toggle_blank())

        # Bind 'h' key for help on presenter window only
        self.presenter_window.window.bind("<h>", lambda e: self.show_help())
        self.presenter_window.window.bind("<H>", lambda e: self.show_help())

        # Help window reference
        self.help_window = None

        # Initial display
        self.root.after(100, self.update_display)

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
  Close window    Quit application
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

        if action == "next" and self.current_slide < self.num_slides - 1:
            self.current_slide += 1
        elif action == "prev" and self.current_slide > 0:
            self.current_slide -= 1
        elif action == "first":
            self.current_slide = 0
        elif action == "last":
            self.current_slide = self.num_slides - 1
        elif action == "goto" and value is not None:
            # User inputs 1-indexed slide number
            target = value - 1
            if 0 <= target < self.num_slides:
                self.current_slide = target
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
        # Audience sees odd pages (0, 2, 4... in 0-indexed = pages 1, 3, 5...)
        audience_page = self.current_slide * 2

        # Presenter sees even pages (1, 3, 5... in 0-indexed = pages 2, 4, 6...)
        presenter_page = self.current_slide * 2 + 1

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

        # Render and display presenter page (always visible, even when blanked)
        pw = self.presenter_window.canvas.winfo_width()
        ph = self.presenter_window.canvas.winfo_height()
        if pw > 10 and ph > 10:
            presenter_pixmap = self.render_page(presenter_page, pw, ph)
            self.presenter_window.display_page(presenter_pixmap)

        # Update window titles
        slide_info = f"Slide {self.current_slide + 1}/{self.num_slides}"
        blank_indicator = " [BLANKED]" if self.is_blanked else ""
        self.audience_window.set_title(f"Audience View - {slide_info}{blank_indicator}")
        self.presenter_window.set_title(f"Presenter Notes - {slide_info}{blank_indicator}")

    def quit(self):
        """Clean up and exit."""
        self.doc.close()
        self.root.quit()

    def run(self):
        """Start the application."""
        print(f"Loaded: {self.pdf_path.name}")
        print(f"Total pages: {self.total_pages}, Slides: {self.num_slides}")
        print("\nControls:")
        print("  Right/Space/PgDn - Next slide")
        print("  Left/PgUp        - Previous slide")
        print("  Home             - First slide")
        print("  End              - Last slide")
        print("  B                - Blank/unblank audience screen")
        print("  H                - Show help (presenter window)")
        print("  F11              - Toggle fullscreen")
        print("  Escape           - Exit fullscreen")
        print("  Number+Enter     - Go to slide number")
        print("\nDrag 'Audience View' to projector, press F11 for fullscreen.")

        self.root.mainloop()


def main():
    if len(sys.argv) != 2:
        print("Usage: python presenter.py <pdf_file>")
        print("\nThe PDF should have interleaved pages:")
        print("  - Odd pages (1, 3, 5...): Audience slides")
        print("  - Even pages (2, 4, 6...): Presenter notes")
        sys.exit(1)

    pdf_path = sys.argv[1]
    presenter = PDFPresenter(pdf_path)
    presenter.run()


if __name__ == "__main__":
    main()

