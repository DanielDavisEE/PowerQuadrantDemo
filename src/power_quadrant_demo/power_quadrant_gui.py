import abc
import cmath
import logging
import tkinter as tk
from tkinter import ttk

import numpy as np
from matplotlib import patches
from matplotlib import ticker
from matplotlib.backend_bases import MouseButton
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg)
from matplotlib.figure import Figure

from gui_components import MyFrame, QuadrantViewer, WaveformViewer, GraphOptionsPane

logging.basicConfig(level=logging.INFO)


class PowerQuadrantsGUI(MyFrame):
    def __init__(self):
        super().__init__(self.state.root)

        self.state.root.wm_title("Power Quadrants")

        self.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        left_block = ttk.Frame(self.frame)
        left_block.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        QuadrantViewer(left_block).pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=5, pady=5)
        GraphOptionsPane(left_block).pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=5, pady=5)
        WaveformViewer(self.frame).pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)

    def init(self):
        super().init()

        self.state.root.resizable(False, False)
        self.state.root.eval('tk::PlaceWindow . center')
        self.state.root.minsize(self.state.root.winfo_width(), self.state.root.winfo_height())

    def mainloop(self):
        self.init()
        self.root.mainloop()


def power_quadrants_gui():
    gui = PowerQuadrantsGUI()
    gui.mainloop()


if __name__ == "__main__":
    power_quadrants_gui()
