"""
View component of the GUI
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


class MyFrame(ttk.Frame, metaclass=abc.ABCMeta):
    """
    An abstract base class for custom
    """
    gui_instances = set()

    def __init__(self, parent, model):
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.debug('Running __init__')

        super().__init__(parent)

        style = ttk.Style()
        style.configure('Header.TLabel', font=('Helvetica', 14))
        style.configure('SubHeader.TLabel', font=('Helvetica', 12))
        style.configure('Text.TLabel', font=('Helvetica', 12))
        style.configure('Text.TRadiobutton', font=('Helvetica', 12))

        self.model = model

        self.gui_instances.add(self)

    @classmethod
    def setup_all(cls):
        """
        Runs the setup method of all gui components contained by the view
        """
        for instance in cls.gui_instances:
            instance.setup()

    @classmethod
    def refresh_all(cls):
        """
        Runs the refresh method of all gui components contained by the view
        """
        for instance in cls.gui_instances:
            instance.refresh()

    def setup(self):
        """
        An optional method for running additional setup code after __init__
        """
        self.log.debug('Running setup')

    def refresh(self):
        """
        An optional method for updating the component during the mainloop
        """


class GraphBlock(MyFrame, metaclass=abc.ABCMeta):
    """
    An abstract base class for GUI blocks which are matplotlib graphs
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.canvas = None
        self.transient_plot_objects = []

    def setup(self):
        super().setup()

    def create_canvas(self, fig: Figure) -> FigureCanvasTkAgg:
        """
        From a given matplotlib Figure, create and return a canvas which has been added to the figure
        """
        canvas = FigureCanvasTkAgg(fig, master=self)  # A tk.DrawingArea.
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        return canvas

    def refresh(self, *_):
        self.clear_temporary_objects()
        self.create_temporary_objects()

        self.canvas.draw()

    def clear_temporary_objects(self):
        for _ in range(len(self.transient_plot_objects)):
            self.transient_plot_objects.pop().remove()

    @abc.abstractmethod
    def create_temporary_objects(self): ...


class QuadrantViewer(GraphBlock):
    """
    A graph representing the four quadrant power unit circle
    """
    DIMENSIONS = 7, 7

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ax = None
        self._button_held = False

    def setup(self):
        super().setup()

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

            if event.inaxes:
                self.model.process_power_phasor_change(event.xdata, event.ydata)

    def _button_release_handler(self, event):
        if event.button == MouseButton.LEFT:
            self._button_held = False

    def _motion_notify_handler(self, event):
        if self._button_held and event.inaxes:
            self.model.process_power_phasor_change(event.xdata, event.ydata)

    def create_temporary_objects(self):
        apparent_power = self.model.voltage_rms.get() * self.model.current_rms.get()
        power_angle = self.model.power_angle.get()

        arc_radius = 0.1
        if apparent_power > arc_radius:
            # Plot angle arc
            angle_deg = np.rad2deg(power_angle)
            theta1, theta2 = 0, angle_deg
            if angle_deg < 0:
                theta1, theta2 = theta2, theta1
            e2 = patches.Arc((0, 0), arc_radius * 2, arc_radius * 2,
                             theta1=theta1, theta2=theta2, linewidth=1, color='gray', alpha=0.8)
            self.transient_plot_objects.append(e2)
            self.ax.add_patch(e2)

        # Convert power_angle to rectangular and plot the vector
        x = apparent_power * np.cos(power_angle)
        y = apparent_power * np.sin(power_angle)
        self.transient_plot_objects.append(self.ax.plot([0, x], [0, y], '--', color='gray')[0])
        self.transient_plot_objects.append(self.ax.plot(x, y, 'r.', markersize=10)[0])

        # Label with the value of power_angle of PF
        self.transient_plot_objects.append(self.ax.text(0.02, 0.02, f'φ = {self.model.power_angle.str_var.get()}',
                                                        fontfamily='monospace'))

        horizontal_alignment = {
            0: 'left',
            1: 'center',
            2: 'right'
        }[round(abs(power_angle), 1) // (np.pi / 3)]
        vertical_alignment = {
            True: 'bottom',
            False: 'top'
        }[power_angle > 0]
        x = apparent_power * 1.05 * np.cos(power_angle)
        y = apparent_power * 1.05 * np.sin(power_angle)
        self.transient_plot_objects.append(self.ax.text(x, y, f'PF = {self.model.power_factor.str_var.get()}',
                                                        fontfamily='monospace',
                                                        ha=horizontal_alignment, va=vertical_alignment))


class WaveformViewer(GraphBlock):
    """
    The section of the GUI which displays the voltage, current and power waveforms
    """
    DIMENSIONS = 6, 9
    MIN_TIME, MAX_TIME = -10, 30
    PERIOD = 20
    OMEGA = 2 * np.pi / PERIOD

    SQRT_TWO = 2 ** 0.5

    def __init__(self, parent, model):
        super().__init__(parent, model)

        self.upper_ax = None
        self.middle_ax = None
        self.lower_ax = None

        self.time_array = np.linspace(self.MIN_TIME, self.MAX_TIME, 100)
        self.phase_array = np.exp(1j * self.OMEGA * self.time_array)

    def setup(self):
        super().setup()

        fig = Figure(figsize=self.DIMENSIONS, dpi=100)
        self.canvas = self.create_canvas(fig)

        peak_power = (self.SQRT_TWO * self.model.voltage_rms.get()) * (self.SQRT_TWO * self.model.current_rms.get())

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

    def create_temporary_objects(self):
        # Plot waveforms on the upper axis
        power_sign = np.sign(np.cos(self.model.power_angle.get()))

        # Plot waveforms on the upper axis
        voltage_plot = self.upper_ax.plot('time', 'voltage', data=self.model.waveforms,
                                          color='r', label='Voltage', zorder=3)[0]
        current_plot = self.upper_ax.plot('time', 'current', data=self.model.waveforms,
                                          color='g', label='Current', alpha=1.0 if power_sign > 0 else 0.3)[0]
        current_inverse_plot = self.upper_ax.plot(self.model.waveforms['time'], -self.model.waveforms['current'],
                                                  color='g', alpha=0.3 if power_sign > 0 else 1.0)[0]
        self.transient_plot_objects.extend([voltage_plot, current_plot, current_inverse_plot])

        # Plot current waveforms on the middle axis
        active_current_plot = self.middle_ax.plot('time', 'active_current', data=self.model.waveforms,
                                                  color='b', label='Active Current')[0]
        reactive_current_plot = self.middle_ax.plot('time', 'reactive_current', data=self.model.waveforms,
                                                    color='orange', label='Reactive Current')[0]
        summed_current_plot = self.middle_ax.plot('time', 'summed_current', data=self.model.waveforms,
                                                  color='k', linestyle='--', label='Apparent Current')[0]
        self.transient_plot_objects.extend([active_current_plot, reactive_current_plot, summed_current_plot])

        # Plot power waveforms on the lower axis
        active_power_plot = self.lower_ax.plot('time', 'active_power', data=self.model.waveforms,
                                               color='blue', label='Active Power')[0]
        reactive_power_plot = self.lower_ax.plot('time', 'reactive_power', data=self.model.waveforms,
                                                 color='orange', label='Reactive Power')[0]
        apparent_power_wave = self.lower_ax.plot('time', 'apparent_power', data=self.model.waveforms,
                                                 color='k', linestyle='--', label='Apparent Power')[0]
        self.transient_plot_objects.extend([active_power_plot, reactive_power_plot, apparent_power_wave])


class GraphOptionsPane(MyFrame):
    """
    The section of the GUI which shows some values and provides some options
    """

    def __init__(self, parent, model):
        super().__init__(parent, model)

        variables_frame = ttk.Frame(self)
        variables_frame.pack(
            side=tk.TOP, fill=tk.BOTH, expand=True)

        row_1 = [self.model.voltage_rms, self.model.current_rms, self.model.cos_phi]
        row_2 = [self.model.apparent_power, self.model.active_power, self.model.reactive_power]

        column_count = max(len(row_1), len(row_2))
        for j in range(column_count):
            col_frame = ttk.Frame(variables_frame)
            col_frame.grid(
                row=0, column=j, sticky=tk.EW, padx=5, pady=5)

            for i, row in enumerate([row_1, row_2]):
                if i >= len(row):
                    continue

                ttk.Label(col_frame, text=f'{row[j].name}', style='Text.TLabel').grid(
                    row=i, column=0, sticky=tk.W, padx=(5, 0), pady=5)
                ttk.Label(col_frame, text='=', style='Text.TLabel').grid(
                    row=i, column=1, sticky=tk.W, padx=0, pady=5)
                ttk.Label(col_frame, textvariable=row[j].str_var, style='Text.TLabel', width=4, anchor='e').grid(
                    row=i, column=2, sticky=tk.W, padx=(0, 5), pady=5)

        pf_convention_frame = ttk.Frame(self)
        pf_convention_frame.pack(
            side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(pf_convention_frame, text='PF Sign Convention:', style='Text.TLabel').pack(
            side=tk.LEFT, fill=tk.BOTH, expand=False
        )
        for sign_convention in ['EEI', 'IEC']:
            ttk.Radiobutton(pf_convention_frame,
                            text=sign_convention,
                            value=sign_convention,
                            variable=self.model.pf_sign_convention,
                            style='Text.TRadiobutton').pack(
                side=tk.LEFT, fill=tk.BOTH, expand=False, padx=10, pady=5)


class View:
    """
    The view component of the MVC gui model
    """

    def __init__(self, root, model):
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.debug('Running __init__')

        self.root = root

        self.frame = ttk.Frame(root)
        self.frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        left_block = ttk.Frame(self.frame)
        left_block.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        QuadrantViewer(left_block, model).pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        GraphOptionsPane(left_block, model).pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        WaveformViewer(self.frame, model).pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup(self):
        """
        Runs the setup method of all gui components contained by the view
        """
        MyFrame.setup_all()

    def refresh(self):
        """
        Runs the refresh method of all gui components contained by the view
        """
        MyFrame.refresh_all()
