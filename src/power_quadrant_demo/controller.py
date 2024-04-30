"""
Controller component of the GUI
"""

import tkinter as tk

import numpy as np

from model import Model
from view import View


class Controller:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Power Quadrants")

        self.model = Model(self.root)
        self.view = View(self.root, self.model)
        self.view.setup()
        self.view.refresh()

        self.model.state_count.trace_add('write', lambda *_: self.refresh())

    def refresh(self):
        self.model.refresh()

        self.view.waveforms = self.model.waveforms
        self.view.refresh()

    def run(self):
        self.root.deiconify()
        self.root.resizable(False, False)
        self.root.eval('tk::PlaceWindow . center')
        self.root.minsize(self.root.winfo_width(), self.root.winfo_height())

        self.root.mainloop()
