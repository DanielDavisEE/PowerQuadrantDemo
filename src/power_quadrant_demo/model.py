"""
Model component of the GUI
"""

import cmath
import logging
import tkinter as tk
from tkinter import ttk

import numpy as np
import pandas as pd


class VersatileVar:
    def __init__(self, master=None, value=None, name=None, *, width=None, precision=2):
        self.name = self._name = name

        self.float_var = tk.DoubleVar(master, value=value, name=name)

        if width is None:
            width = ''

        self.str_format = f'{{:z{width}.{precision}f}}'
        self.str_var = tk.StringVar(master, value=self.str_format.format(value), name=f'{name}Str')

    def set(self, value):
        self.float_var.set(value)
        self.str_var.set(self.str_format.format(value))

    def get(self):
        return self.float_var.get()

    def trace_add(self, mode, callback):
        self.float_var.trace_add(mode, callback)

    def __repr__(self):
        return self.float_var.get()

    def __str__(self):
        return self.str_var.get()


class Model:
    """
    A shared state container for the power quadrant gui
    """
    DIMENSIONS = 6, 9
    MIN_TIME, MAX_TIME = -10, 30
    PERIOD = 20
    OMEGA = 2 * np.pi / PERIOD

    SQRT_TWO = 2 ** 0.5

    def __init__(self, root):
        self.log = logging.getLogger('Model')

        self.root = root

        style = ttk.Style(self.root)
        style.configure('Header.TLabel', font=('Helvetica', 14))
        style.configure('SubHeader.TLabel', font=('Helvetica', 12))
        style.configure('Text.TLabel', font=('Helvetica', 12))
        style.configure('Text.TRadiobutton', font=('Helvetica', 12))

        # State variables
        self.voltage_rms = VersatileVar(self.root, name='Vms', value=1.)
        self.voltage_angle = VersatileVar(self.root, name='VoltageTheta', value=0.)
        self.current_rms = VersatileVar(self.root, name='Irms', value=1.)
        self.phi = VersatileVar(self.root, name='Phi', value=0., width=5)
        self.pf_sign_convention = tk.StringVar(name='SignConvention', value='EEI')

        # Derived State Variables
        self.current_angle = VersatileVar(self.root, name='CurrentTheta', value=0.)
        self.cos_phi = VersatileVar(self.root, name='cos(φ)', value=1.)
        self.power_factor = VersatileVar(self.root, name='PF', value=1.)
        self.apparent_power = VersatileVar(self.root, name='S', value=1.)
        self.active_power = VersatileVar(self.root, name='R', value=1.)
        self.reactive_power = VersatileVar(self.root, name='Q', value=0.)

        self.phi.trace_add('write', lambda *_: self.refresh())
        self.pf_sign_convention.trace_add('write', lambda *_: self.refresh())

        self.pf_sign_conversions = {
            'EEI': lambda pf: pf * -np.sign(np.sin(self.phi.get())),
            'IEC': lambda pf: pf
        }

        self.waveforms = pd.DataFrame([], columns=['time', 'phase', 'voltage', 'current',
                                                   'active_current', 'reactive_current', 'summed_current',
                                                   'active_power', 'reactive_power', 'apparent_power',
                                                   ])
        self.state_count = tk.IntVar(name='StateCount', value=0)

        self.waveforms['time'] = np.linspace(self.MIN_TIME, self.MAX_TIME, 100)
        self.waveforms['phase'] = np.exp(1j * self.OMEGA * self.waveforms['time'])

        self.refresh()

        self.log.debug('Configured model')

    def process_power_phasor_change(self, x_coord, y_coord):
        """
        Takes the coordinates of a quadrant graph input and updates phi accordingly
        """
        self.phi.set(np.arctan2(y_coord, x_coord))
        apparent_power = min(1., (y_coord ** 2 + x_coord ** 2) ** 0.5)
        self.current_rms.set(apparent_power / self.voltage_rms.get())

    def refresh(self):
        """
        Update the waveforms based on changes to voltage, current or power angle
        """
        # Update derived state variables
        self.current_angle.set(self.voltage_angle.get() - self.phi.get())
        self.cos_phi.set(np.cos(self.phi.get()))
        self.power_factor.set(self.pf_sign_conversions[self.pf_sign_convention.get()](self.cos_phi.get()))

        apparent_power = self.voltage_rms.get()* self.current_rms.get()
        active_power = apparent_power * np.cos(self.phi.get())
        reactive_power = apparent_power * np.sin(self.phi.get())

        self.apparent_power.set(apparent_power)
        self.active_power.set(active_power)
        self.reactive_power.set(reactive_power)

        # Convert voltage/current rms values to phasors
        voltage_phasor = self.SQRT_TWO * self.voltage_rms.get() * cmath.rect(1., self.voltage_angle.get())
        current_phasor = self.SQRT_TWO * self.current_rms.get() * cmath.rect(1., self.current_angle.get())

        # Build waveforms from phasors
        self.waveforms['voltage'] = np.real(voltage_phasor * self.waveforms['phase'])
        self.waveforms['current'] = np.real(current_phasor * self.waveforms['phase'])

        self.waveforms['active_current'] = np.real(np.real(current_phasor) * self.waveforms['phase'])
        self.waveforms['reactive_current'] = np.real(np.imag(current_phasor) * self.waveforms['phase'] * 1j)
        self.waveforms['summed_current'] = self.waveforms['active_current'] + self.waveforms['reactive_current']

        self.waveforms['active_power'] = self.waveforms['voltage'] * self.waveforms['active_current']
        self.waveforms['reactive_power'] = self.waveforms['voltage'] * self.waveforms['reactive_current']
        self.waveforms['apparent_power'] = self.waveforms['voltage'] * self.waveforms['current']

        self.state_count.set((self.state_count.get() + 1) % 0xff)
