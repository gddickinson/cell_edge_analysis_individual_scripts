"""
Help window for the Cell Edge Movement Analysis GUI.

Builds a Toplevel with a section list on the left and a scrollable text pane on
the right. Content comes from ``gui_help_content.HELP_SECTIONS`` so the prose can
be edited independently of the layout.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

from gui_help_content import HELP_SECTIONS, ABOUT_TEXT


def show_about(parent):
    """Show the small About dialog."""
    messagebox.showinfo("About", ABOUT_TEXT, parent=parent)


def show_help_window(parent):
    """Open (or focus) the Analysis Guide window."""
    # Reuse a single window if already open
    existing = getattr(parent, "_help_window", None)
    if existing is not None:
        try:
            existing.deiconify()
            existing.lift()
            return existing
        except tk.TclError:
            pass  # was destroyed; rebuild

    win = tk.Toplevel(parent)
    win.title("Analysis Guide - Cell Edge Movement Analysis")
    win.geometry("980x680")
    parent._help_window = win

    # Left: section list
    left = ttk.Frame(win, padding=(8, 8))
    left.pack(side="left", fill="y")
    ttk.Label(left, text="Sections", font=("TkDefaultFont", 10, "bold")).pack(anchor="w")

    listbox = tk.Listbox(left, width=32, height=30, exportselection=False,
                         activestyle="dotbox")
    listbox.pack(fill="y", expand=True, pady=4)
    for title, _ in HELP_SECTIONS:
        listbox.insert("end", title)

    # Right: text pane
    right = ttk.Frame(win, padding=(8, 8))
    right.pack(side="left", fill="both", expand=True)
    text = scrolledtext.ScrolledText(right, wrap="word", font=("Courier", 11),
                                     padx=10, pady=10)
    text.pack(fill="both", expand=True)

    def show_section(index):
        if not (0 <= index < len(HELP_SECTIONS)):
            return
        _, body = HELP_SECTIONS[index]
        text.configure(state="normal")
        text.delete("1.0", "end")
        text.insert("1.0", body)
        text.configure(state="disabled")

    def on_select(_event=None):
        sel = listbox.curselection()
        if sel:
            show_section(sel[0])

    listbox.bind("<<ListboxSelect>>", on_select)

    # Close button
    ttk.Button(left, text="Close", command=win.destroy).pack(fill="x", pady=(4, 0))

    # Start on the overview
    listbox.selection_set(0)
    show_section(0)

    win.lift()
    return win
