#!/usr/bin/env python3
"""
Hand-labeling app — draw the cell edge on EVERY frame and export a mask stack
that can be substituted for the DIC mask in the analysis pipeline.

Draw: left-drag on the image to trace the boundary (the outer edge of the cell /
bright PIEZO1 region). "Copy prev" duplicates the previous frame's label so you
only tweak it (fast for a movie). "Seed from auto-edge" drops in the automated
guess to correct. Labels autosave and resume.

Export: "Export mask (.tif)" writes a binary mask stack (cell = below the drawn
line, by default) at the original image dimensions. Substitute it for the
dataset's *_Mask.tif, or run step1 with --mask-stack-path <that file>.

Run:
    cd fluorescence_edge_experiments/labeling
    python label_app.py
    python label_app.py --data-dir <step1_results dir>
"""

import os
import sys
import argparse
import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
for p in (_HERE, _PARENT):
    if p not in sys.path:
        sys.path.insert(0, p)
import label_io
import edge_methods as em
try:
    import detector
    _HAVE_DETECTOR = True
except Exception:
    _HAVE_DETECTOR = False

DEFAULT_DATA = os.path.join(os.path.dirname(_PARENT), 'data', 'test_1',
                            'analysis_results', 'step1_results')


class LabelApp:
    def __init__(self, root, data_dir, label_dir):
        self.root = root
        root.title("Cell-edge labeler — draw every frame, export mask")
        root.geometry("1280x920")

        self.images = np.load(os.path.join(data_dir, 'images.npy'))
        self.masks = np.load(os.path.join(data_dir, 'masks.npy'))
        self.n = self.images.shape[0]
        self.h, self.w = self.images.shape[1], self.images.shape[2]
        self.label_dir = label_dir
        os.makedirs(label_dir, exist_ok=True)

        self.segments_by_frame = label_io.load_labels(label_dir)
        self.current = 0
        self.drawing = False
        self.cur_pts = []
        self.background = None
        self.cur_line = None

        self.show_dic = tk.BooleanVar(value=True)
        self.show_auto = tk.BooleanVar(value=False)
        self.cell_side = tk.StringVar(value='below')
        self._auto_cache = {}

        self._build_ui()
        self.render()

    # ----------------------------------------------------------------- UI
    def _build_ui(self):
        top = ttk.Frame(self.root, padding=6)
        top.pack(side='top', fill='x')
        ttk.Button(top, text="◄◄", width=4, command=lambda: self.goto(0)).pack(side='left')
        ttk.Button(top, text="◄", width=4, command=lambda: self.step(-1)).pack(side='left', padx=2)
        ttk.Button(top, text="►", width=4, command=lambda: self.step(1)).pack(side='left')
        ttk.Button(top, text="►►", width=4, command=lambda: self.goto(self.n - 1)).pack(side='left', padx=2)
        self.slider = ttk.Scale(top, from_=0, to=self.n - 1, orient='horizontal',
                                command=self._on_slider)
        self.slider.pack(side='left', fill='x', expand=True, padx=10)
        ttk.Label(top, text="frame:").pack(side='left')
        self.goto_var = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.goto_var, width=5)
        ent.pack(side='left')
        ent.bind('<Return>', lambda _e: self.goto_typed())
        ttk.Button(top, text="Go", command=self.goto_typed).pack(side='left', padx=2)
        ttk.Button(top, text="Next unlabelled", command=self.next_unlabelled).pack(side='left', padx=8)

        body = ttk.Frame(self.root)
        body.pack(side='top', fill='both', expand=True)
        left = ttk.Frame(body, padding=6)
        left.pack(side='left', fill='y')
        ttk.Label(left, text="Frames", font=('TkDefaultFont', 10, 'bold')).pack(anchor='w')
        self.listbox = tk.Listbox(left, width=18, height=30, exportselection=False)
        self.listbox.pack(fill='y', expand=True)
        self.listbox.bind('<<ListboxSelect>>', self.on_list_select)
        self.progress = ttk.Label(left, text="")
        self.progress.pack(anchor='w', pady=4)

        right = ttk.Frame(body)
        right.pack(side='left', fill='both', expand=True)
        self.fig = Figure(figsize=(9, 8))
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        tb = ttk.Frame(right)
        tb.pack(side='top', fill='x')
        self.toolbar = NavigationToolbar2Tk(self.canvas, tb)
        self.toolbar.update()
        self.canvas.mpl_connect('draw_event', self._on_draw_event)
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.canvas.mpl_connect('button_release_event', self.on_release)

        bot = ttk.Frame(self.root, padding=6)
        bot.pack(side='bottom', fill='x')
        ttk.Button(bot, text="Copy prev label", command=self.copy_prev).pack(side='left')
        if _HAVE_DETECTOR:
            ttk.Button(bot, text="Seed from auto-edge", command=self.seed_auto).pack(side='left', padx=2)
        ttk.Button(bot, text="Undo stroke", command=self.undo_stroke).pack(side='left', padx=2)
        ttk.Button(bot, text="Clear frame", command=self.clear_frame).pack(side='left', padx=2)
        ttk.Label(bot, text="  cell is").pack(side='left')
        ttk.Combobox(bot, textvariable=self.cell_side, values=['below', 'above'],
                     state='readonly', width=6).pack(side='left')
        ttk.Label(bot, text="the line").pack(side='left')
        ttk.Checkbutton(bot, text="DIC", variable=self.show_dic, command=self.render).pack(side='left', padx=(10, 0))
        ttk.Checkbutton(bot, text="auto", variable=self.show_auto, command=self.render).pack(side='left')
        ttk.Button(bot, text="Export mask (.tif)", command=self.export_mask).pack(side='right')

        self.root.bind('<Left>', lambda _e: self.step(-1))
        self.root.bind('<Right>', lambda _e: self.step(1))
        self._refresh_listbox()

    def _refresh_listbox(self):
        self.listbox.delete(0, 'end')
        labelled = 0
        for f in range(self.n):
            done = bool(self.segments_by_frame.get(f))
            labelled += done
            self.listbox.insert('end', f"[{'✓' if done else ' '}] frame {f}")
        self.progress.config(text=f"{labelled}/{self.n} labelled")
        self.listbox.selection_clear(0, 'end')
        self.listbox.selection_set(self.current)
        self.listbox.see(self.current)

    # ------------------------------------------------------------- helpers
    def segs(self):
        return self.segments_by_frame.setdefault(self.current, [])

    def auto_for(self, f):
        if not _HAVE_DETECTOR:
            return None
        if f not in self._auto_cache:
            try:
                self._auto_cache[f] = detector.fluor_edge(self.images[f], self.masks[f])
            except Exception:
                self._auto_cache[f] = np.full(self.w, np.nan)
        return self._auto_cache[f]

    # ------------------------------------------------------------- drawing
    def render(self):
        self.ax.clear()
        img = self.images[self.current]
        self.ax.imshow(img, cmap='gray',
                       vmin=np.percentile(img, 1), vmax=np.percentile(img, 99.5))
        x = np.arange(self.w)
        if self.show_dic.get():
            self.ax.plot(x, em.edge_dic(img, self.masks[self.current]),
                         '-', color='red', lw=1.0, alpha=0.4, label='DIC edge')
        if self.show_auto.get() and _HAVE_DETECTOR:
            self.ax.plot(x, self.auto_for(self.current), '-', color='lime',
                         lw=1.0, alpha=0.5, label='auto-edge')
        y = label_io.segments_to_yx(self.segs(), self.w, self.h)
        self.ax.plot(x, y, '-', color='yellow', lw=2.2, label='your label')
        self.cur_line, = self.ax.plot([], [], '-', color='orange', lw=1.6)
        self.ax.set_title(f"Frame {self.current} / {self.n - 1}   "
                          f"(strokes: {len(self.segs())})", fontsize=12)
        self.ax.legend(loc='upper right', fontsize=8)
        self.ax.axis('off')
        self.fig.tight_layout()
        self.canvas.draw()

    def _on_draw_event(self, _e):
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)

    def on_press(self, event):
        if event.button != 1 or event.inaxes != self.ax:
            return
        if getattr(self.toolbar, 'mode', ''):
            return
        self.drawing = True
        self.cur_pts = [(event.xdata, event.ydata)]

    def on_motion(self, event):
        if not self.drawing or event.inaxes != self.ax:
            return
        self.cur_pts.append((event.xdata, event.ydata))
        pts = np.asarray(self.cur_pts)
        self.cur_line.set_data(pts[:, 0], pts[:, 1])
        if self.background is not None:
            self.canvas.restore_region(self.background)
            self.ax.draw_artist(self.cur_line)
            self.canvas.blit(self.ax.bbox)
        else:
            self.canvas.draw_idle()

    def on_release(self, event):
        if not self.drawing:
            return
        self.drawing = False
        if len(self.cur_pts) >= 2:
            self.segs().append([[float(a), float(b)] for a, b in self.cur_pts])
            self.autosave()
        self.cur_pts = []
        self.render()

    # ------------------------------------------------------------- actions
    def copy_prev(self):
        if self.current > 0 and self.segments_by_frame.get(self.current - 1):
            self.segments_by_frame[self.current] = [
                [list(p) for p in s] for s in self.segments_by_frame[self.current - 1]]
            self.autosave()
            self.render()

    def seed_auto(self):
        y = self.auto_for(self.current)
        if y is None:
            return
        x = np.arange(self.w)
        ok = np.isfinite(y)
        if ok.sum() >= 2:
            self.segs().append([[float(a), float(b)] for a, b in zip(x[ok], y[ok])])
            self.autosave()
            self.render()

    def undo_stroke(self):
        if self.segs():
            self.segs().pop()
            self.autosave()
            self.render()

    def clear_frame(self):
        self.segments_by_frame[self.current] = []
        self.autosave()
        self.render()

    def autosave(self):
        label_io.save_labels(self.label_dir, self.segments_by_frame, self.w, self.h)
        self._refresh_listbox()

    def export_mask(self):
        import tifffile
        rows = np.arange(self.h)[:, None]
        below = self.cell_side.get() == 'below'
        stack = np.zeros((self.n, self.h, self.w), np.uint8)
        n_hand = n_fb = n_empty = 0
        for f in range(self.n):
            segs = self.segments_by_frame.get(f)
            y = label_io.segments_to_yx(segs, self.w, self.h) if segs else None
            if y is not None and np.isfinite(y).sum() >= 2:
                with np.errstate(invalid='ignore'):
                    fill = (rows >= y[None, :]) if below else (rows <= y[None, :])
                stack[f][fill] = 255
                n_hand += 1
            elif self.masks is not None:
                stack[f] = (self.masks[f] > 0).astype(np.uint8) * 255
                n_fb += 1
            else:
                n_empty += 1
            # extend the region to the left/right image edges
            label_io.extend_mask_frame(stack[f])
        out = os.path.join(self.label_dir, 'labeled_mask.tif')
        tifffile.imwrite(out, stack)
        messagebox.showinfo(
            "Mask exported",
            f"{n_hand} hand-labelled frame(s), {n_fb} filled from DIC fallback.\n\n"
            f"Saved: {out}\n\n"
            f"To use it: replace the dataset's *_Mask.tif with this file, or run\n"
            f"step1_data_loading.py --mask-stack-path \"{out}\"")

    # ---------------------------------------------------------- navigation
    def goto(self, f):
        self.current = int(np.clip(f, 0, self.n - 1))
        self.slider.set(self.current)
        self._refresh_listbox()
        self.render()

    def step(self, d):
        self.goto(self.current + d)

    def goto_typed(self):
        try:
            self.goto(int(self.goto_var.get()))
        except (ValueError, TypeError):
            pass

    def next_unlabelled(self):
        order = list(range(self.current + 1, self.n)) + list(range(0, self.current))
        for f in order:
            if not self.segments_by_frame.get(f):
                self.goto(f)
                return

    def _on_slider(self, val):
        f = int(round(float(val)))
        if f != self.current:
            self.current = f
            self._refresh_listbox()
            self.render()

    def on_list_select(self, _e):
        sel = self.listbox.curselection()
        if sel:
            self.goto(int(sel[0]))


def main():
    p = argparse.ArgumentParser(description='Draw the cell edge on every frame; export a mask')
    p.add_argument('--data-dir', default=DEFAULT_DATA)
    p.add_argument('--label-dir', default=os.path.join(_HERE, 'labels'))
    args = p.parse_args()
    root = tk.Tk()
    LabelApp(root, args.data_dir, args.label_dir)
    root.mainloop()


if __name__ == '__main__':
    main()
