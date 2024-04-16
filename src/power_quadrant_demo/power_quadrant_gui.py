import logging
import tkinter as tk
from tkinter import ttk
import abc

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


class GUIBlock(abc.ABC):
    root = tk.Tk()

    style = ttk.Style(root)
    style.configure('Header.TLabel', font=('Helvetica', 14))
    style.configure('SubHeader.TLabel', font=('Helvetica', 12))

    phi = RoundedDoubleVar(root, name='GraphPhi', value=0.)

    def __init__(self, parent):
        super().__init__()

        self.frame = ttk.Frame(parent)

        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.DEBUG)

    def __getattr__(self, item):
        if item in {'pack', 'grid', 'place'}:
            pass_through_f = getattr(self.frame, item)
            return pass_through_f


class GraphBlock(GUIBlock, metaclass=abc.ABCMeta):
    REFRESH_DELAY_MS = 20

    def __init__(self, parent):
        super().__init__(parent)

        self.canvas = None
        self.transient_plot_objects = []

        self.setup()
        self._refresh()

    def _refresh(self):
        for _ in range(len(self.transient_plot_objects)):
            self.transient_plot_objects.pop().remove()

        self.refresh()

        self.canvas.draw()

        self.root.after(self.REFRESH_DELAY_MS, self._refresh)

    def create_canvas(self, fig: Figure) -> FigureCanvasTkAgg:
        canvas = FigureCanvasTkAgg(fig, master=self.frame)  # A tk.DrawingArea.
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        return canvas

    @abc.abstractmethod
    def setup(self):
        pass

    @abc.abstractmethod
    def refresh(self):
        pass


class QuadrantViewer(GraphBlock):
    DIMENSIONS = 5, 5

    def __init__(self, parent):
        self.ax = None

        super().__init__(parent)

    def setup(self):
        fig = Figure(figsize=self.DIMENSIONS, dpi=100)
        self.canvas = self.create_canvas(fig)

        self.ax = fig.add_subplot(111)

        # Plot lines on graph
        phi_array = np.linspace(0, 2 * np.pi, 100)
        self.ax.axvline(0, -1.1, 1.1, color='k', linewidth=1)
        self.ax.axhline(0, -1.1, 1.1, color='k', linewidth=1)
        self.ax.plot(np.sin(phi_array), np.cos(phi_array), 'k')

        self.ax.annotate('+P', xy=(0.94, 0.51), xycoords='axes fraction')
        self.ax.annotate('-P', xy=(0.01, 0.51), xycoords='axes fraction')
        self.ax.annotate('+Q  (OverExcited)', xy=(0.43, 0.96), xycoords='axes fraction')
        self.ax.annotate('-Q  (UnderExcited)', xy=(0.45, 0.02), xycoords='axes fraction')

        self.ax.set_xlim(-1.2, 1.2)
        self.ax.set_ylim(-1.2, 1.2)

    def refresh(self):
        x, y = np.cos(self.phi.get()), np.sin(self.phi.get())
        self.transient_plot_objects.append(self.ax.plot(x, y, 'r.', markersize=10)[0])
        self.transient_plot_objects.append(self.ax.plot([0, x], [0, y], '--', color='gray')[0])


class WaveformViewer(GraphBlock):
    DIMENSIONS = 5, 5
    MIN_TIME, MAX_TIME = -10, 30

    def __init__(self, *args, **kwargs):
        self.time_array = np.linspace(self.MIN_TIME, self.MAX_TIME, 100)
        self.phi_array = self.time_array / (self.MAX_TIME - self.MIN_TIME) * np.pi * 4

        self.upper_ax = None
        self.lower_ax = None

        super().__init__(*args, **kwargs)

    def setup(self):
        fig = Figure(figsize=self.DIMENSIONS, dpi=100)
        self.canvas = self.create_canvas(fig)

        self.upper_ax = fig.add_subplot(211)
        self.lower_ax = fig.add_subplot(212)

        self.upper_ax.plot(self.time_array, np.sin(self.phi_array), 'r', label='Voltage')

        self.refresh()

        self.upper_ax.legend(loc='upper right')
        self.lower_ax.legend(loc='upper right')

    def refresh(self):
        current_plot = self.upper_ax.plot(self.time_array, np.sin(self.phi_array - self.phi.get()), 'g', label='Current')[0]
        current_alpha_plot = self.upper_ax.plot(self.time_array, np.sin(self.phi_array - self.phi.get() - np.pi), 'g', label='Reverse Current', alpha=0.3)[0]
        self.transient_plot_objects.append(current_plot)
        self.transient_plot_objects.append(current_alpha_plot)

        active_magnitude = np.cos(self.phi.get())
        active_wave = self.lower_ax.plot(self.time_array, active_magnitude * np.sin(self.phi_array), 'b', label='Active Current')[0]

        reactive_magnitude = np.sin(self.phi.get())
        reactive_wave = self.lower_ax.plot(self.time_array, reactive_magnitude * np.sin(self.phi_array - np.pi / 2), color='orange', label='Reactive Current')[0]

        self.transient_plot_objects.extend([active_wave, reactive_wave])


class GraphOptionsPane(GUIBlock):
    def __init__(self, parent):
        super().__init__(parent)

        phi_scale_frame = ttk.Frame(self.frame)
        phi_scale_frame.pack(
            side=tk.TOP, fill=tk.BOTH, expand=False)
        phi_scale_frame.columnconfigure(2, weight=1)

        ttk.Label(phi_scale_frame, text='Phi =').grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(phi_scale_frame, textvariable=self.phi, width=8).grid(
            row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Scale(phi_scale_frame, variable=self.phi, from_=-np.pi, to=np.pi).grid(
            row=0, column=2, sticky=tk.EW, padx=5, pady=5)

        self.phi.trace_add('write', self._round_vars)

        variables_frame = ttk.Frame(self.frame)
        variables_frame.pack(
            side=tk.TOP, fill=tk.BOTH, expand=False)

        self.rms_voltage = RoundedDoubleVar(name='Vrms', value=1)
        self.cos_phi_pf = RoundedDoubleVar(name='cos(phi)')
        self.p_over_s_pf = RoundedDoubleVar(name='P/S')
        row_1 = [self.rms_voltage, self.cos_phi_pf, self.p_over_s_pf]

        self.apparent_current = RoundedDoubleVar(name='Ia', value=1)
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
        for var_name in [
            'phi',
            'rms_voltage', 'cos_phi_pf', 'p_over_s_pf',
            'apparent_current', 'active_current', 'reactive_current',
            'apparent_power', 'active_power', 'reactive_power',
        ]:
            var = getattr(self, var_name)
            var.set(round(var.get(), 2))

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
        super().__init__(self.root)

        self.root.wm_title("Power Quadrants")

        self.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        graph_block = ttk.Frame(self.frame)
        graph_block.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        QuadrantViewer(graph_block).pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)
        WaveformViewer(graph_block).pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)
        GraphOptionsPane(self.frame).pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=5, pady=5)

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
