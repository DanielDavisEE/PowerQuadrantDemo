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

        self.model = Model()
        self.view = View(self.model)
        self.view.setup()

        self.model.state_count.trace_add('write', self.refresh)

    def update_display_variables(self):
        self.view.phi_str.set(f"{self.model.phi:z5.2f}")

        self.view.voltage_str.set(f"{self.model.voltage:z.2f}")
        self.view.current_str.set(f"{self.model.current:z.2f}")
        self.view.cos_phi_str.set(f"{np.cos(self.model.phi):z.2f}")

        apparent_power = self.model.voltage * self.model.current
        active_power = apparent_power * np.cos(self.model.phi)
        reactive_power = apparent_power * np.sin(self.model.phi)

        self.view.apparent_power_str.set(f"{apparent_power:z.2f}")
        self.view.active_power_str.set(f"{active_power:z.2f}")
        self.view.reactive_power_str.set(f"{reactive_power:z.2f}")

    def refresh(self):
        self.model.refresh()

        self.update_display_variables()
        self.view.waveforms = self.model.waveforms
        self.view.refresh()

    def run(self):
        self.root.deiconify()
        self.root.resizable(False, False)
        self.root.eval('tk::PlaceWindow . center')
        self.root.minsize(self.root.winfo_width(), self.root.winfo_height())

        self.root.mainloop()
