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

    phi = tk.DoubleVar(root, name='GraphPhi', value=0.)

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

    def refresh(self):
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
        x, y = np.cos(self.phi.get()), np.sin(self.phi.get())
        self.transient_plot_objects.append(self.ax.plot([0, x], [0, y], '--', color='gray')[0])
        self.transient_plot_objects.append(self.ax.plot(x, y, 'r.', markersize=10)[0])

        # Label with the value of phi
        self.transient_plot_objects.append(self.ax.annotate(f'φ = {self.phi.get()}', xy=(0.51, 0.51), xycoords='axes fraction'))


class WaveformViewer(GraphBlock):
    """
    The section of the GUI which displays the
    """
    DIMENSIONS = 5, 5
    MIN_TIME, MAX_TIME = -10, 30

    SQRT_TWO = 2 ** 0.5

    def __init__(self, *args, **kwargs):
        self.upper_ax = None
        self.lower_ax = None

        self.time_array = np.linspace(self.MIN_TIME, self.MAX_TIME, 100)
        self.phi_array = self.time_array / (self.MAX_TIME - self.MIN_TIME) * np.pi * 4

        super().__init__(*args, **kwargs)

    def setup(self):
        fig = Figure(figsize=self.DIMENSIONS, dpi=100)
        self.canvas = self.create_canvas(fig)

        self.upper_ax = fig.add_subplot(211)
        self.lower_ax = fig.add_subplot(212)

        self.upper_ax.plot(self.time_array, self.SQRT_TWO * np.sin(self.phi_array), 'r', label='Voltage', zorder=10)

        self.refresh()

        self.upper_ax.legend(loc='upper right')
        self.lower_ax.legend(loc='upper right')

    def refresh(self):
        # Plot waveforms on the upper axis
        active_power = np.cos(self.phi.get())
        apparent_current = self.SQRT_TWO * np.sin(self.phi_array - self.phi.get())
        current_plot = self.upper_ax.plot(self.time_array, apparent_current,
                                          'g', label='Current', alpha=1.0 if active_power > 0 else 0.3)[0]
        current_alpha_plot = self.upper_ax.plot(self.time_array, -apparent_current,
                                                'g', alpha=0.3 if active_power > 0 else 1.0)[0]
        self.transient_plot_objects.extend([current_plot, current_alpha_plot])

        # Plot waveforms on the lower axis
        active_wave = self.SQRT_TWO * np.cos(self.phi.get()) * np.sin(self.phi_array)
        active_wave_plot = self.lower_ax.plot(self.time_array, active_wave,
                                              'b', label='Active Current')[0]

        reactive_wave = self.SQRT_TWO * np.sin(self.phi.get()) * np.sin(self.phi_array - np.pi / 2)
        reactive_wave_plot = self.lower_ax.plot(self.time_array, reactive_wave,
                                                color='orange', label='Reactive Current')[0]

        summed_wave = active_wave + reactive_wave
        summed_wave_plot = self.lower_ax.plot(self.time_array, summed_wave,
                                              color='k', label='Apparent Current')[0]

        self.transient_plot_objects.extend([active_wave_plot, reactive_wave_plot, summed_wave_plot])


class GraphOptionsPane(GUIBlock):
    def __init__(self, parent):
        super().__init__(parent)

        phi_scale_frame = ttk.Frame(self.frame)
        phi_scale_frame.pack(
            side=tk.TOP, fill=tk.BOTH, expand=False)
        phi_scale_frame.columnconfigure(2, weight=1)

        self.phi.trace_add('write', self._round_vars)

        variables_frame = ttk.Frame(self.frame)
        variables_frame.pack(
            side=tk.TOP, fill=tk.BOTH, expand=False)

        self.rms_voltage = tk.DoubleVar(name='Vrms', value=1)
        self.cos_phi_pf = tk.DoubleVar(name='cos(phi)')
        self.p_over_s_pf = tk.DoubleVar(name='P/S')
        row_1 = [self.rms_voltage, self.cos_phi_pf, self.p_over_s_pf]

        self.apparent_current = tk.DoubleVar(name='Ia', value=1)
        self.active_current = tk.DoubleVar(name='I')
        self.reactive_current = tk.DoubleVar(name='Ir')
        row_2 = [self.apparent_current, self.active_current, self.reactive_current]

        self.apparent_power = tk.DoubleVar(name='S')
        self.active_power = tk.DoubleVar(name='P')
        self.reactive_power = tk.DoubleVar(name='Q')
        row_3 = [self.apparent_power, self.active_power, self.reactive_power]

        self.phi.trace_add('write', self._calculate_variables)

        for i, row in enumerate([row_1, row_2, row_3]):
            for j, var in enumerate(row):
                ttk.Label(variables_frame, text=f'{var._name} =', style='Text.TLabel').grid(
                    row=i, column=2 * j, sticky=tk.W, padx=5, pady=5)
                ttk.Label(variables_frame, textvariable=var, style='Text.TLabel', width=6, justify='right').grid(
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
