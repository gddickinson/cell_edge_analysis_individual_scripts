#!/usr/bin/env python3
"""
Review the detected fluorescence cell edge across the whole movie.

Scrub frames with the slider, the ◄/► buttons, or the Left/Right arrow keys.
The detected edge (cyan) is shown over the PIEZO1 image with the DIC edge (red)
for comparison and your hand label (yellow dashed) on frames you labelled.

Reads review/out/detected_edges.npz if present (run run_detector.py first for
instant scrubbing); otherwise computes each frame on demand and caches it.
Read-only on the pipeline.
"""

import os
import sys
import json
import argparse
import numpy as np
import tkinter as tk
from tkinter import ttk

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
sys.path.insert(0, _PARENT)
import detector
import edge_methods as em

DATA = os.path.join(os.path.dirname(_PARENT), 'data', 'test_1',
                    'analysis_results', 'step1_results')
LABELS = os.path.join(_PARENT, 'labeling', 'labels', 'labels.json')


class ReviewApp:
    def __init__(self, root, data_dir):
        self.root = root
        root.title("Detected fluorescence edge — movie review")
        root.geometry("1180x900")
        self.images = np.load(os.path.join(data_dir, 'images.npy'))
        self.masks = np.load(os.path.join(data_dir, 'masks.npy'))
        self.n = self.images.shape[0]
        self.w = self.images.shape[2]

        self.edges = self._load_precomputed()
        self.edge_cache = {}
        self.dic_cache = {}
        self.labels = self._load_labels()

        self.show_det = tk.BooleanVar(value=True)
        self.show_dic = tk.BooleanVar(value=True)
        self.show_lab = tk.BooleanVar(value=True)
        self.current = 0
        self._build_ui()
        self.render()

    # ---------------------------------------------------------------- data
    def _load_precomputed(self):
        path = os.path.join(_HERE, 'out', 'detected_edges.npz')
        if os.path.exists(path):
            try:
                return np.load(path)['edges']
            except Exception:
                pass
        return None

    def _load_labels(self):
        if not os.path.exists(LABELS):
            return {}
        try:
            d = json.load(open(LABELS))
        except (json.JSONDecodeError, OSError):
            return {}
        out = {}
        for k, fr in d.get('frames', {}).items():
            out[int(k)] = np.array([np.nan if v is None else v for v in fr['y']], float)
        return out

    def edge_for(self, f):
        if self.edges is not None:
            return self.edges[f]
        if f not in self.edge_cache:
            self.edge_cache[f] = detector.fluor_edge(self.images[f], self.masks[f])
        return self.edge_cache[f]

    def dic_for(self, f):
        if f not in self.dic_cache:
            self.dic_cache[f] = em.edge_dic(self.images[f], self.masks[f])
        return self.dic_cache[f]

    # ------------------------------------------------------------------ UI
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
        e = ttk.Entry(top, textvariable=self.goto_var, width=5)
        e.pack(side='left')
        e.bind('<Return>', lambda _e: self.goto_typed())
        ttk.Button(top, text="Go", command=self.goto_typed).pack(side='left', padx=2)

        toggles = ttk.Frame(self.root, padding=(6, 0))
        toggles.pack(side='top', fill='x')
        ttk.Checkbutton(toggles, text="detected (cyan)", variable=self.show_det,
                        command=self.render).pack(side='left')
        ttk.Checkbutton(toggles, text="DIC (red)", variable=self.show_dic,
                        command=self.render).pack(side='left', padx=10)
        ttk.Checkbutton(toggles, text="your label (yellow)", variable=self.show_lab,
                        command=self.render).pack(side='left')
        self.info = ttk.Label(toggles, text="", font=('TkDefaultFont', 10, 'bold'))
        self.info.pack(side='right')

        self.fig = Figure(figsize=(9, 8))
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        tb = ttk.Frame(self.root)
        tb.pack(side='bottom', fill='x')
        NavigationToolbar2Tk(self.canvas, tb).update()

        self.root.bind('<Left>', lambda _e: self.step(-1))
        self.root.bind('<Right>', lambda _e: self.step(1))

    # ------------------------------------------------------------- drawing
    def render(self):
        self.ax.clear()
        img = self.images[self.current]
        self.ax.imshow(img, cmap='gray',
                       vmin=np.percentile(img, 1), vmax=np.percentile(img, 99.5))
        x = np.arange(self.w)
        dic = self.dic_for(self.current)
        det = self.edge_for(self.current)
        if self.show_dic.get():
            self.ax.plot(x, dic, '-', color='red', lw=1.0, alpha=0.5, label='DIC edge')
        if self.show_det.get():
            self.ax.plot(x, det, '-', color='deepskyblue', lw=2.0, label='detected edge')
        labelled = self.current in self.labels
        if self.show_lab.get() and labelled:
            self.ax.plot(x, self.labels[self.current], '--', color='yellow',
                         lw=1.8, label='your label')
        m = np.isfinite(det) & np.isfinite(dic)
        shift = np.median(np.abs(det[m] - dic[m])) if m.any() else np.nan
        tag = '  [LABELLED]' if labelled else ''
        self.ax.set_title(f'Frame {self.current} / {self.n - 1}   '
                          f'(detected shifted {shift:.0f}px from DIC){tag}', fontsize=12)
        self.ax.legend(loc='upper right', fontsize=9)
        self.ax.axis('off')
        self.fig.tight_layout()
        self.canvas.draw()
        self.info.config(text=f"{self.current + 1}/{self.n}")

    # ---------------------------------------------------------- navigation
    def goto(self, f):
        self.current = int(np.clip(f, 0, self.n - 1))
        self.slider.set(self.current)
        self.render()

    def step(self, d):
        self.goto(self.current + d)

    def goto_typed(self):
        try:
            self.goto(int(self.goto_var.get()))
        except (ValueError, TypeError):
            pass

    def _on_slider(self, val):
        f = int(round(float(val)))
        if f != self.current:
            self.current = f
            self.render()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--data-dir', default=DATA)
    args = p.parse_args()
    root = tk.Tk()
    ReviewApp(root, args.data_dir)
    root.mainloop()


if __name__ == '__main__':
    main()
