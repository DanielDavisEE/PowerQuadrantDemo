import logging
import tkinter as tk
from tkinter import ttk

import numpy as np
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg)
from matplotlib.figure import Figure

logging.basicConfig(level=logging.INFO)

class Limiter(ttk.Scale):
    """ ttk.Scale sublass that limits the precision of values.
    Source: https://stackoverflow.com/questions/54186639/tkinter-control-ttk-scales-increment-as-with-tk-scale-and-a-tk-doublevar
    """

    def __init__(self, *args, **kwargs):
        self.precision = kwargs.pop('precision')  # Remove non-std kwarg.
        self.chain = kwargs.pop('command', lambda *a: None)  # Save if present.

        super().__init__(*args, command=self._value_changed, **kwargs)

    def _value_changed(self, newvalue):
        newvalue = round(float(newvalue), self.precision)
        self.winfo_toplevel().globalsetvar(self.cget('variable'), (newvalue))
        self.chain(newvalue)  # Call user specified function.

class RoundedDoubleVar(tk.DoubleVar):
    """ ttk.Scale sublass that limits the precision of values.
    Source: https://stackoverflow.com/questions/54186639/tkinter-control-ttk-scales-increment-as-with-tk-scale-and-a-tk-doublevar
    """

    def get(self) -> float:
        return round(super().get(), 2)



class GUIBlock:
    root = tk.Tk()

    style = ttk.Style(root)
    style.configure('Header.TLabel', font=('Helvetica', 14))
    style.configure('SubHeader.TLabel', font=('Helvetica', 12))

    phi = RoundedDoubleVar(root, name='GraphPhi', value=0.)

    def __init__(self, parent=None):
        super().__init__()

        if parent:
            self.frame = ttk.Frame(parent.frame)
            parent.children.append(self)
        else:
            self.frame = ttk.Frame(self.root)

        self.children = []

        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.DEBUG)

    def __getattr__(self, item):
        if item in {'pack', 'grid', 'place'}:
            pass_through_f = getattr(self.frame, item)
            return pass_through_f

    def _refresh(self):
        for child in self.children:
            child._refresh()


class GraphBlock(GUIBlock):
    DIMENSIONS: tuple[int, int]

    def __init__(self, parent):
        super().__init__(parent)

        self.transient_plot_objects = []

        self.plot_constant_objects()
        self.plot_transient_objects()
        self.canvas.draw()

    def _refresh(self):
        super()._refresh()

        for _ in range(len(self.transient_plot_objects)):
            self.transient_plot_objects.pop().remove()

        self.plot_transient_objects()

        self.canvas.draw()

    def plot_constant_objects(self):
        fig = Figure(figsize=self.DIMENSIONS, dpi=100)
        self.ax = fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(fig, master=self.frame)  # A tk.DrawingArea.
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.draw()

    def plot_transient_objects(self):
        raise NotImplementedError


class QuadrantViewer(GraphBlock):
    DIMENSIONS = 5, 5

    def plot_constant_objects(self):
        super().plot_constant_objects()

        # Plot lines on graph
        phi_array = np.linspace(0, 2 * np.pi, 100)
        self.ax.axvline(0, -1.1, 1.1, color='k')
        self.ax.axhline(0, -1.1, 1.1, color='k')
        self.ax.plot(np.sin(phi_array), np.cos(phi_array), 'k')

    def plot_transient_objects(self):
        x, y = np.cos(self.phi.get()), np.sin(self.phi.get())
        self.transient_plot_objects.append(self.ax.plot(x, y, 'r.', markersize=10)[0])
        self.transient_plot_objects.append(self.ax.plot([0, x], [0, y], '--', color='gray')[0])


class WaveformViewer(GraphBlock):
    DIMENSIONS = 5, 2

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        min_time, max_time = -10, 30
        self.time_array = np.linspace(min_time, max_time, 100)
        self.phi_array = self.time_array / (max_time - min_time) * np.pi * 4

    def plot_constant_objects(self):
        super().plot_constant_objects()

        self.ax.plot(self.time_array, np.sin(self.phi_array), 'r', label='Voltage')
        self.transient_plot_objects.append(self.ax.plot(self.time_array, np.sin(self.phi_array), 'g', label='Current')[0])

        self.ax.legend(loc='upper right')

    def plot_transient_objects(self):
        self.transient_plot_objects.append(self.ax.plot(self.time_array, np.sin(self.phi_array), 'g')[0])


class GraphOptionsPane(GUIBlock):
    def __init__(self, parent):
        super().__init__(parent)

        phi_scale_frame = ttk.Frame(self.frame)
        phi_scale_frame.pack(
            side=tk.TOP, fill=tk.BOTH, expand=False)
        phi_scale_frame.columnconfigure(2, weight=1)

        ttk.Label(phi_scale_frame, text='Phi=').grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(phi_scale_frame, textvariable=self.phi, width=8).grid(
            row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Scale(phi_scale_frame, variable=self.phi, from_=-np.pi, to=np.pi).grid(
            row=0, column=2, sticky=tk.EW, padx=5, pady=5)

        self.phi.trace_add('write', self._round_vars)

        variables_frame = ttk.Frame(self.frame)
        variables_frame.pack(
            side=tk.TOP, fill=tk.BOTH, expand=False)

        self.rms_voltage = RoundedDoubleVar(name='Vrms', value=230)
        self.cos_phi_pf = RoundedDoubleVar(name='cos(phi)')
        self.p_over_s_pf = RoundedDoubleVar(name='P/S')
        row_1 = [self.rms_voltage, self.cos_phi_pf, self.p_over_s_pf]

        self.apparent_current = RoundedDoubleVar(name='Ia', value=200)
        self.active_current = RoundedDoubleVar(name='I')
        self.reactive_current = RoundedDoubleVar(name='Ir')
        row_2 = [self.apparent_current, self.active_current, self.reactive_current]

        self.apparent_power = RoundedDoubleVar(name='S')
        self.active_power = RoundedDoubleVar(name='P')
        self.reactive_power = RoundedDoubleVar(name='Q')
        row_3 = [self.apparent_power, self.active_power, self.reactive_power]

        self.phi.trace_add('write', self._calculate_variables)

        for i, row in enumerate([row_1, row_2, row_3]):
            for j, var in enumerate(row):
                ttk.Label(variables_frame, text=f'{var._name} =').grid(
                    row=i, column=2 * j, sticky=tk.W, padx=5, pady=5)
                ttk.Label(variables_frame, textvariable=var).grid(
                    row=i, column=2 * j + 1, sticky=tk.W, padx=5, pady=5)

    def _round_vars(self, *_):
        self.phi.set(round(self.phi.get(), 2))

        self.rms_voltage.set(round(self.rms_voltage.get(), 2))
        self.cos_phi_pf.set(round(self.cos_phi_pf.get(), 2))
        self.p_over_s_pf.set(round(self.p_over_s_pf.get(), 2))

        self.apparent_current.set(round(self.apparent_current.get(), 2))
        self.active_current.set(round(self.active_current.get(), 2))
        self.reactive_current.set(round(self.reactive_current.get(), 2))

        self.apparent_power.set(round(self.apparent_power.get(), 2))
        self.active_power.set(round(self.active_power.get(), 2))
        self.reactive_power.set(round(self.reactive_power.get(), 2))

    def _calculate_variables(self, *_):
        self.cos_phi_pf.set(np.cos(self.phi.get()))

        self.active_current.set(self.apparent_current.get() * np.cos(self.phi.get()))
        self.reactive_current.set(self.apparent_current.get() * np.sin(self.phi.get()))

        self.apparent_power.set(self.rms_voltage.get() * self.apparent_current.get())
        self.active_power.set(self.apparent_power.get() * np.cos(self.phi.get()))
        self.reactive_power.set(self.apparent_current.get() * np.sin(self.phi.get()))

        self.p_over_s_pf.set(self.active_power.get() / self.apparent_power.get())



class PowerQuadrantsGUI(GUIBlock):
    def __init__(self):
        super().__init__()

        self.root.wm_title("Power Quadrants")

        self.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        QuadrantViewer(self).pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=5, pady=5)
        WaveformViewer(self).pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=5, pady=5)
        GraphOptionsPane(self).pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=5, pady=5)

        self.phi.trace_add('write', lambda *_: self._refresh())
        self.phi.set(0.)

        self.root.resizable(False, False)
        self.root.eval('tk::PlaceWindow . center')
        self.root.minsize(self.root.winfo_width(), self.root.winfo_height())

    def mainloop(self):
        self.root.mainloop()


def power_quadrants_gui():
    gui = PowerQuadrantsGUI()
    gui.mainloop()


if __name__ == "__main__":
    power_quadrants_gui()
