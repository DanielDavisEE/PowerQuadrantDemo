"""

"""

import abc
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

from state_info import PowerQuadrantState


class MyFrame(ttk.Frame, metaclass=abc.ABCMeta):
    """
    An abstract base class for
    """
    state = PowerQuadrantState()

    _gui_block_instances = set()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._gui_block_instances.add(self)

        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.DEBUG)

    # @classmethod
    # def init(cls):
    #     """
    #     """
    #     for inst in cls._gui_block_instances:
    #         inst._setup()
    #
    # def _setup(self):
    #     """
    #     Method to allow metaclasses to control the setup workflow
    #     """
    #     self.setup()
    #
    # def setup(self):
    #     """
    #     An optional method for running additional setup code after __init__
    #     """


class GraphBlock(MyFrame, metaclass=abc.ABCMeta):
    """
    An abstract base class for GUI blocks which are matplotlib graphs
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.canvas = None
        self.transient_plot_objects = []

        self.state.state_count.trace_add('write', self._refresh)

    def _setup(self, *_):
        super()._setup()

        self.refresh()

        self.canvas.draw()

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
    def setup(self): ...

    @abc.abstractmethod
    def refresh(self): ...


class QuadrantViewer(GraphBlock):
    """
    A graph representing the four quadrant power unit circle
    """
    DIMENSIONS = 7, 7

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ax = None
        self._button_held = False
        self.phi_str = tk.StringVar(name='PhiStr', value=f"{self.state.phi:z5.2f}")

        self.state.state_count.trace_add('write', lambda *_: self.phi_str.set(f"{self.state.phi:z5.2f}"))

    def setup(self):
        fig = Figure(figsize=self.DIMENSIONS, dpi=100)
        self.canvas = self.create_canvas(fig)
        self.canvas.mpl_connect('button_press_event', self._button_press_handler)
        self.canvas.mpl_connect('button_release_event', self._button_release_handler)
        self.canvas.mpl_connect('motion_notify_event', self._motion_notify_handler)

        self.ax = fig.add_subplot(111, xticks=[0], yticks=[0])

        self.ax.xaxis.set_minor_locator(ticker.MultipleLocator(0.5))
        self.ax.xaxis.set_minor_formatter('{x:.1f}')

        self.ax.yaxis.set_minor_locator(ticker.MultipleLocator(0.5))
        self.ax.yaxis.set_minor_formatter('{x:.1f}')

        self.ax.grid(visible=True)

        # Plot lines on graph
        phi_array = np.linspace(0, 2 * np.pi, 100)
        self.ax.plot(np.sin(phi_array), np.cos(phi_array), 'k')

        self.ax.annotate('+P', xy=(0.94, 0.51), xycoords='axes fraction')
        self.ax.annotate('-P', xy=(0.01, 0.51), xycoords='axes fraction')
        self.ax.annotate('+Q  (OverExcited)', xy=(0.45, 0.96), xycoords='axes fraction')
        self.ax.annotate('-Q  (UnderExcited)', xy=(0.46, 0.02), xycoords='axes fraction')

        self.ax.set_xlim(-1.4, 1.4)
        self.ax.set_ylim(-1.4, 1.4)

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
        apparent_power = self.state.voltage_rms * self.state.current_rms

        arc_radius = 0.1
        if apparent_power > arc_radius:
            # Plot angle arc
            angle_deg = np.rad2deg(self.state.phi)
            theta1, theta2 = 0, angle_deg
            if angle_deg < 0:
                theta1, theta2 = theta2, theta1
            e2 = patches.Arc((0, 0), arc_radius * 2, arc_radius * 2,
                             theta1=theta1, theta2=theta2, linewidth=1, color='gray', alpha=0.8)
            self.transient_plot_objects.append(e2)
            self.ax.add_patch(e2)

        # Convert phi to rectangular and plot the vector
        x = apparent_power * np.cos(self.state.phi)
        y = apparent_power * np.sin(self.state.phi)
        self.transient_plot_objects.append(self.ax.plot([0, x], [0, y], '--', color='gray')[0])
        self.transient_plot_objects.append(self.ax.plot(x, y, 'r.', markersize=10)[0])

        # Label with the value of phi of PF
        self.transient_plot_objects.append(self.ax.text(0.02, 0.02, f'φ = {self.phi_str.get()}', fontfamily='monospace'))

        horizontal_alignment = {
            0: 'left',
            1: 'center',
            2: 'right'
        }[round(abs(self.state.phi), 1) // (np.pi / 3)]
        vertical_alignment = {
            True: 'bottom',
            False: 'top'
        }[self.state.phi > 0]
        x = apparent_power * 1.05 * np.cos(self.state.phi)
        y = apparent_power * 1.05 * np.sin(self.state.phi)
        self.transient_plot_objects.append(self.ax.text(x, y, f'PF = {self.state.power_factor:z.2f}', fontfamily='monospace',
                                                        ha=horizontal_alignment, va=vertical_alignment))


class WaveformViewer(GraphBlock):
    """
    The section of the GUI which displays the
    """
    DIMENSIONS = 6, 9
    MIN_TIME, MAX_TIME = -10, 30
    PERIOD = 20
    OMEGA = 2 * np.pi / PERIOD

    SQRT_TWO = 2 ** 0.5

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.upper_ax = None
        self.middle_ax = None
        self.lower_ax = None

        self.time_array = np.linspace(self.MIN_TIME, self.MAX_TIME, 100)
        self.phase_array = np.exp(1j * self.OMEGA * self.time_array)

    def setup(self):
        fig = Figure(figsize=self.DIMENSIONS, dpi=100)
        self.canvas = self.create_canvas(fig)

        peak_power = (self.SQRT_TWO * self.voltage.get()) * (self.SQRT_TWO * self.current.get())

        self.upper_ax, self.middle_ax, self.lower_ax = fig.subplots(
            nrows=3, ncols=1, sharex=True, sharey=True,
            subplot_kw=dict(xticks=[0], yticks=[0],
                            xlim=(self.MIN_TIME, self.MAX_TIME),
                            ylim=(-peak_power * 1.1, peak_power * 1.1)),
        )

        self.upper_ax.xaxis.set_minor_locator(ticker.MultipleLocator(5))
        self.upper_ax.xaxis.set_minor_formatter('{x:.0f}')

        self.upper_ax.yaxis.set_minor_locator(ticker.MultipleLocator(0.5))
        self.upper_ax.yaxis.set_minor_formatter('{x:.1f}')

        self.upper_ax.grid(visible=True)
        self.middle_ax.grid(visible=True)
        self.lower_ax.grid(visible=True)

        self.upper_ax.set_title('Voltage/Current Waveforms')
        self.middle_ax.set_title('Current Decomposition')
        self.lower_ax.set_title('Power Decomposition')

        self.lower_ax.set_xlabel('Time (ms)')

        self.refresh()

        self.upper_ax.legend(loc='upper right')
        self.middle_ax.legend(loc='upper right')
        self.lower_ax.legend(loc='upper right')

    def refresh(self):
        # Plot waveforms on the upper axis
        power_sign = np.sign(np.cos(self.phi.get()))

        # Plot waveforms on the upper axis
        voltage_plot = self.upper_ax.plot('time', 'voltage', data=self.state.waveforms,
                                          color='r', label='Voltage', zorder=3)[0]
        current_plot = self.upper_ax.plot('time', 'current', data=self.state.waveforms,
                                          color='g', label='Current', alpha=1.0 if power_sign > 0 else 0.3)[0]
        current_inverse_plot = self.upper_ax.plot('time', -self.state.waveforms['current'], data=self.state.waveforms,
                                                  color='g', alpha=0.3 if power_sign > 0 else 1.0)[0]
        self.transient_plot_objects.extend([voltage_plot, current_plot, current_inverse_plot])

        # Plot current waveforms on the middle axis
        active_current_plot = self.middle_ax.plot('time', 'active_current', data=self.state.waveforms,
                                                  color='b', label='Active Current')[0]
        reactive_current_plot = self.middle_ax.plot('time', 'reactive_current', data=self.state.waveforms,
                                                    color='orange', label='Reactive Current')[0]
        summed_current_plot = self.middle_ax.plot('time', 'summed_current', data=self.state.waveforms,
                                                  color='--k', label='Apparent Current')[0]
        self.transient_plot_objects.extend([active_current_plot, reactive_current_plot, summed_current_plot])

        # Plot power waveforms on the lower axis
        active_power_plot = self.lower_ax.plot('time', 'active_power', data=self.state.waveforms,
                                               color='blue', label='Active Power')[0]
        reactive_power_plot = self.lower_ax.plot('time', 'reactive_power', data=self.state.waveforms,
                                                 color='orange', label='Reactive Power')[0]
        apparent_power_wave = self.lower_ax.plot('time', 'apparent_power', data=self.state.waveforms,
                                                 color='--k', label='Apparent Power')[0]
        self.transient_plot_objects.extend([active_power_plot, reactive_power_plot, apparent_power_wave])


class GraphOptionsPane(MyFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.phi.trace_add('write', self._calculate_variables)
        self.voltage.trace_add('write', self._calculate_variables)
        self.current.trace_add('write', self._calculate_variables)

        variables_frame = ttk.Frame(self.frame)
        variables_frame.pack(
            side=tk.TOP, fill=tk.BOTH, expand=True)

        self.voltage_str = tk.StringVar(name='Vrms')
        self.current_str = tk.StringVar(name='Irms')
        self.cos_phi_str = tk.StringVar(name='cos(φ)')
        row_1 = [self.voltage_str, self.current_str, self.cos_phi_str]

        self.apparent_power_str = tk.StringVar(name='S')
        self.active_power_str = tk.StringVar(name='P')
        self.reactive_power_str = tk.StringVar(name='Q')
        row_2 = [self.apparent_power_str, self.active_power_str, self.reactive_power_str]

        column_count = max(len(row_1), len(row_2))

        for j in range(column_count):
            col_frame = ttk.Frame(variables_frame)
            col_frame.grid(
                row=0, column=j, sticky=tk.EW, padx=5, pady=5)

            for i, row in enumerate([row_1, row_2]):
                if i >= len(row):
                    continue

                ttk.Label(col_frame, text=f'{row[j]._name}', style='Text.TLabel').grid(
                    row=i, column=0, sticky=tk.W, padx=(5, 0), pady=5)
                ttk.Label(col_frame, text=f'=', style='Text.TLabel').grid(
                    row=i, column=1, sticky=tk.W, padx=0, pady=5)
                ttk.Label(col_frame, textvariable=row[j], style='Text.TLabel', width=4, anchor='e').grid(
                    row=i, column=2, sticky=tk.W, padx=(0, 5), pady=5)

        pf_convention_frame = ttk.Frame(self.frame)
        pf_convention_frame.pack(
            side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(pf_convention_frame, text='PF Sign Convention:', style='Text.TLabel').pack(
            side=tk.LEFT, fill=tk.BOTH, expand=False
        )
        for sign_convention in ['EEI', 'IEC']:
            ttk.Radiobutton(pf_convention_frame,
                            text=sign_convention,
                            value=sign_convention,
                            variable=self.pf_sign_convention,
                            style='Text.TRadiobutton').pack(
                side=tk.LEFT, fill=tk.BOTH, expand=False, padx=10, pady=5)

    def setup(self):
        self._calculate_variables()

    def _calculate_variables(self, *_):
        self.voltage_str.set(f"{self.voltage.get():z.2f}")
        self.current_str.set(f"{self.current.get():z.2f}")
        self.cos_phi_str.set(f"{np.cos(self.phi.get()):z.2f}")

        apparent_power = self.voltage.get() * self.current.get()
        active_power = apparent_power * np.cos(self.phi.get())
        reactive_power = apparent_power * np.sin(self.phi.get())

        self.apparent_power_str.set(f"{apparent_power:z.2f}")
        self.active_power_str.set(f"{active_power:z.2f}")
        self.reactive_power_str.set(f"{reactive_power:z.2f}")
