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
    The model component of the MVC gui model
    """
    DIMENSIONS = 6, 9
    MIN_TIME, MAX_TIME = -10, 30
    PERIOD = 20
    OMEGA = 2 * np.pi / PERIOD

    SQRT_TWO = 2 ** 0.5

    def __init__(self, root):
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.debug('Running __init__')

        self.root = root

        # Input variables
        self.apparent_power = VersatileVar(self.root, name='S', value=1.)
        self.power_angle = VersatileVar(self.root, name='Phi', value=0., width=5)
        self.pf_sign_convention = tk.StringVar(name='SignConvention', value='EEI')

        # Independent state variables
        self.voltage_rms = VersatileVar(self.root, name='Vms', value=1.)
        self.voltage_angle = VersatileVar(self.root, name='VoltageTheta', value=0.)

        # Dependent state variables
        self.current_rms = VersatileVar(self.root, name='Irms', value=1.)
        self.current_angle = VersatileVar(self.root, name='CurrentTheta', value=0.)
        self.cos_phi = VersatileVar(self.root, name='cos(φ)', value=1.)
        self.power_factor = VersatileVar(self.root, name='PF', value=1.)
        self.active_power = VersatileVar(self.root, name='R', value=1.)
        self.reactive_power = VersatileVar(self.root, name='Q', value=0.)

        # Bind the two input variables to the model refresh method
        self.power_angle.trace_add('write', lambda *_: self.refresh())
        self.pf_sign_convention.trace_add('write', lambda *_: self.refresh())

        self.pf_sign_conversions = {
            'EEI': lambda pf: pf * -np.sign(np.sin(self.power_angle.get())),
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

    def process_power_phasor_change(self, x_coord, y_coord):
        """
        Takes the coordinates of a quadrant graph input and updates power_angle accordingly
        """
        self.apparent_power.set(min(1., (x_coord ** 2 + y_coord ** 2) ** 0.5))
        self.power_angle.set(np.arctan2(y_coord, x_coord))

    def refresh(self):
        """
        Update the waveforms based on changes to voltage, current or power angle
        """
        # Update dependent state variables
        self.current_rms.set(self.apparent_power.get() / self.voltage_rms.get())
        self.current_angle.set(self.voltage_angle.get() - self.power_angle.get())
        self.cos_phi.set(np.cos(self.power_angle.get()))
        self.power_factor.set(self.pf_sign_conversions[self.pf_sign_convention.get()](self.cos_phi.get()))
        self.active_power.set(self.apparent_power.get() * np.cos(self.power_angle.get()))
        self.reactive_power.set(self.apparent_power.get() * np.sin(self.power_angle.get()))

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

        # Increment the state count variable to indicate the model has updated
        self.state_count.set((self.state_count.get() + 1) % 0xff)
