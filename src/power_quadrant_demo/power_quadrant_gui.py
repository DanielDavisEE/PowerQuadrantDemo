import abc
import logging
import tkinter as tk
from tkinter import ttk

import numpy as np
from matplotlib import patches
from matplotlib.backend_bases import MouseButton
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg)
from matplotlib.figure import Figure

logging.basicConfig(level=logging.INFO)


class GUIBlock(abc.ABC):
    """
    An abstract base class for
    """
    root = tk.Tk()

    style = ttk.Style(root)
    style.configure('Header.TLabel', font=('Helvetica', 14))
    style.configure('SubHeader.TLabel', font=('Helvetica', 12))
    style.configure('Text.TLabel', font=('Helvetica', 12))

    phi = tk.DoubleVar(root, name='Phi', value=0.)
    voltage = tk.DoubleVar(root, name='VoltageRMS', value=1.)
    current = tk.DoubleVar(root, name='CurrentRMS', value=1.)

    _gui_block_instances = set()

    def __init__(self, parent):
        super().__init__()

        self._gui_block_instances.add(self)

        self.frame = ttk.Frame(parent)

        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.DEBUG)

    def __getattr__(self, item):
        if item in {'pack', 'grid', 'place'}:
            pass_through_f = getattr(self.frame, item)
            return pass_through_f

    @classmethod
    def init(cls):
        for inst in cls._gui_block_instances:
            inst.setup()

    def setup(self):
        """
        An optional method for running additional setup code after __init__
        """


class GraphBlock(GUIBlock, metaclass=abc.ABCMeta):
    """
    An abstract base class for GUI blocks which are matplotlib graphs
    """

    def __init__(self, parent):
        super().__init__(parent)

        self.canvas = None
        self.transient_plot_objects = []

        self.setup()
        self._refresh()
        self.phi.trace_add('write', self._refresh)

    def _refresh(self, *_):
        for _ in range(len(self.transient_plot_objects)):
            self.transient_plot_objects.pop().remove()

        self.refresh()

        self.canvas.draw()

    def create_canvas(self, fig: Figure) -> FigureCanvasTkAgg:
        """
        From a given matplotlib Figure, create and return a canvas which has been added to the
        .
        """
        canvas = FigureCanvasTkAgg(fig, master=self.frame)  # A tk.DrawingArea.
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        return canvas

    @abc.abstractmethod
    def refresh(self):
        pass


class QuadrantViewer(GraphBlock):
    DIMENSIONS = 5, 5

    def __init__(self, parent):
        self.ax = None
        self._button_held = False
        self.phi_str = tk.StringVar(name='PhiStr', value=f"{self.phi.get():5.2f}")

        self.phi.trace_add('write', lambda *_: self.phi_str.set(f"{self.phi.get():5.2f}"))

        super().__init__(parent)

    def setup(self):
        fig = Figure(figsize=self.DIMENSIONS, dpi=100)
        self.canvas = self.create_canvas(fig)
        self.canvas.mpl_connect('button_press_event', self._button_press_handler)
        self.canvas.mpl_connect('button_release_event', self._button_release_handler)
        self.canvas.mpl_connect('motion_notify_event', self._motion_notify_handler)

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

    def _button_press_handler(self, event):
        if event.button == MouseButton.LEFT:
            self._button_held = True
            self._recalculate_phi(event)

    def _button_release_handler(self, event):
        if event.button == MouseButton.LEFT:
            self._button_held = False

    def _motion_notify_handler(self, event):
        if self._button_held:
            self._recalculate_phi(event)

    def _recalculate_phi(self, event):
        if event.inaxes:
            self.phi.set(np.arctan2(event.ydata, event.xdata))
            apparent_power = min(1., (event.ydata ** 2 + event.xdata ** 2) ** 0.5)
            self.current.set(apparent_power / self.voltage.get())

    def refresh(self):
        apparent_power = self.voltage.get() * self.current.get()

        arc_radius = 0.2
        if apparent_power > arc_radius:
            # Plot angle arc
            angle_deg = np.rad2deg(self.phi.get())
            theta1, theta2 = 0, angle_deg
            if angle_deg < 0:
                theta1, theta2 = theta2, theta1
            e2 = patches.Arc((0, 0), 0.2, 0.2,
                             theta1=theta1, theta2=theta2, linewidth=1, color='gray', alpha=0.8)
            self.transient_plot_objects.append(e2)
            self.ax.add_patch(e2)

        # Convert phi to rectangular and plot the vector
        x = apparent_power * np.cos(self.phi.get())
        y = apparent_power * np.sin(self.phi.get())
        self.transient_plot_objects.append(self.ax.plot([0, x], [0, y], '--', color='gray')[0])
        self.transient_plot_objects.append(self.ax.plot(x, y, 'r.', markersize=10)[0])

        # Label with the value of phi
        self.transient_plot_objects.append(self.ax.text(0.02, 0.02, f'φ = {self.phi_str.get()}', fontfamily='monospace'))


class WaveformViewer(GraphBlock):
    """
    The section of the GUI which displays the
    """
    DIMENSIONS = 5, 5
    MIN_TIME, MAX_TIME = -10, 30
    PERIOD = 20
    OMEGA = 2 * np.pi / PERIOD

    SQRT_TWO = 2 ** 0.5

    def __init__(self, *args, **kwargs):
        self.upper_ax = None
        self.lower_ax = None

        self.time_array = np.linspace(self.MIN_TIME, self.MAX_TIME, 100)
        self.voltage_wave = self.SQRT_TWO * np.sin(self.OMEGA * self.time_array)

        super().__init__(*args, **kwargs)

    def setup(self):
        fig = Figure(figsize=self.DIMENSIONS, dpi=100)
        self.canvas = self.create_canvas(fig)

        self.upper_ax = fig.add_subplot(211)
        self.lower_ax = fig.add_subplot(212)

        self.upper_ax.plot(self.time_array, self.voltage_wave, 'r', label='Voltage', zorder=3)

        self.refresh()

        self.upper_ax.legend(loc='upper right')
        self.lower_ax.legend(loc='upper right')

    def refresh(self):
        # Plot waveforms on the upper axis
        power_sign = np.sign(np.cos(self.phi.get()))
        voltage_wave = self.SQRT_TWO * np.sin(self.OMEGA * self.time_array)
        current_wave = self.SQRT_TWO * np.sin(self.OMEGA * self.time_array - self.phi.get()) * self.current.get()

        current_plot = self.upper_ax.plot(self.time_array, current_wave,
                                          'g', label='Current', alpha=1.0 if power_sign > 0 else 0.3)[0]
        current_alpha_plot = self.upper_ax.plot(self.time_array, -current_wave,
                                                'g', alpha=0.3 if power_sign > 0 else 1.0)[0]
        self.transient_plot_objects.extend([current_plot, current_alpha_plot])

        # Plot waveforms on the lower axis
        apparent_power = voltage_wave * current_wave
        # https://www.electronics-tutorials.ws/accircuits/power-in-ac-circuits.html

        # apparent_power_peak = self.SQRT_TWO * self.voltage.get() * self.current.get()
        active_power_wave = apparent_power_peak * np.sin(self.period * self.time_array - self.phi.get())
        active_power_plot = self.lower_ax.plot(self.time_array, active_power_wave,
                                               'b', label='Active Power')[0]

        reactive_power_wave = apparent_power_peak * np.cos(self.period * self.time_array - self.phi.get())
        reactive_power_plot = self.lower_ax.plot(self.time_array, reactive_power_wave,
                                                 color='orange', label='Reactive Power')[0]

        summed_power_wave = active_power_wave + reactive_power_wave
        summed_power_plot = self.lower_ax.plot(self.time_array, summed_power_wave,
                                               color='k', label='Apparent Power')[0]

        self.transient_plot_objects.extend([active_power_plot, reactive_power_plot, summed_power_plot])


class GraphOptionsPane(GUIBlock):
    def __init__(self, parent):
        super().__init__(parent)

        self.phi.trace_add('write', self._calculate_variables)
        self.voltage.trace_add('write', self._calculate_variables)
        self.current.trace_add('write', self._calculate_variables)

        phi_scale_frame = ttk.Frame(self.frame)
        phi_scale_frame.pack(
            side=tk.TOP, fill=tk.BOTH, expand=False)
        phi_scale_frame.columnconfigure(2, weight=1)

        variables_frame = ttk.Frame(self.frame)
        variables_frame.pack(
            side=tk.TOP, fill=tk.BOTH, expand=False)

        self.voltage_str = tk.StringVar(name='Vrms')
        self.current_str = tk.StringVar(name='Irms')
        self.cos_phi_str = tk.StringVar(name='cos(φ)')
        row_1 = [self.voltage_str, self.current_str, self.cos_phi_str]

        self.apparent_power_str = tk.StringVar(name='S')
        self.active_power_str = tk.StringVar(name='P')
        self.reactive_power_str = tk.StringVar(name='Q')
        row_2 = [self.apparent_power_str, self.active_power_str, self.reactive_power_str]

        for i, row in enumerate([row_1, row_2]):
            for j, var in enumerate(row):
                ttk.Label(variables_frame, text=f'{var._name} =', style='Text.TLabel').grid(
                    row=i, column=2 * j, sticky=tk.W, padx=(10, 0), pady=10)
                ttk.Label(variables_frame, textvariable=var, style='Text.TLabel', width=4, anchor='e').grid(
                    row=i, column=2 * j + 1, sticky=tk.W, padx=(0, 10), pady=10)

        self._calculate_variables()

    def _calculate_variables(self, *_):
        self.voltage_str.set(f"{self.voltage.get():.2f}")
        self.current_str.set(f"{self.current.get():.2f}")
        self.cos_phi_str.set(f"{np.cos(self.phi.get()):.2f}")

        apparent_power = self.voltage.get() * self.current.get()
        active_power = apparent_power * np.cos(self.phi.get())
        reactive_power = apparent_power * np.sin(self.phi.get())

        self.apparent_power_str.set(f"{apparent_power:.2f}")
        self.active_power_str.set(f"{active_power:.2f}")
        self.reactive_power_str.set(f"{reactive_power:.2f}")


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
