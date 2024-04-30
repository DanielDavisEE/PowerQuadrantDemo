"""
Model component of the GUI
"""

import cmath
import logging
import tkinter as tk
from tkinter import ttk

import numpy as np
import pandas as pd


class Model:
    """
    A shared state container for the power quadrant gui
    """
    DIMENSIONS = 6, 9
    MIN_TIME, MAX_TIME = -10, 30
    PERIOD = 20
    OMEGA = 2 * np.pi / PERIOD

    SQRT_TWO = 2 ** 0.5

    voltage_rms: float
    voltage_angle: float
    current_rms: float
    current_angle: float
    pf_sign_convention: str

    def __init__(self, root):
        self.log = logging.getLogger('Model')

        self.root = root

        style = ttk.Style(self.root)
        style.configure('Header.TLabel', font=('Helvetica', 14))
        style.configure('SubHeader.TLabel', font=('Helvetica', 12))
        style.configure('Text.TLabel', font=('Helvetica', 12))
        style.configure('Text.TRadiobutton', font=('Helvetica', 12))

        # State variables
        self._voltage_rms = tk.DoubleVar(self.root, name='VoltageRMS', value=1.)
        self._voltage_angle = tk.DoubleVar(self.root, name='VoltageTheta', value=0.)
        self._current_rms = tk.DoubleVar(self.root, name='CurrentRMS', value=1.)
        self._current_angle = tk.DoubleVar(self.root, name='CurrentTheta', value=0.)
        self._pf_sign_convention = tk.StringVar(name='SignConvention', value='EEI')

        self._voltage_rms.trace_add('write', lambda *_: self.refresh())
        self._voltage_angle.trace_add('write', lambda *_: self.refresh())
        self._current_rms.trace_add('write', lambda *_: self.refresh())
        self._current_angle.trace_add('write', lambda *_: self.refresh())
        self._pf_sign_convention.trace_add('write', lambda *_: self.refresh())

        self.pf_sign_conversions = {
            'EEI': lambda phi: np.cos(phi) * -np.sign(np.sin(phi)),
            'IEC': lambda phi: np.cos(phi)
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

    def __getattr__(self, item):
        """
        Streamline getting values from tk Variable state values
        """
        if item[0] != '_' and hasattr(self, '_' + item):
            return getattr(self, '_' + item).get()

        raise AttributeError(f"{self.__class__.__name__} has no attribute '{item}'")


    def __setattr__(self, key, value):
        """
        Streamline setting values from tk Variable state values
        """
        if key[0] != '_' and hasattr(self, '_' + key):
            getattr(self, '_' + key).set(value)
            return

        super().__setattr__(key, value)

    @property
    def phi(self):
        """
        Returns the power angle, phi, from the voltage and current angles
        """
        return self.voltage_angle - self.current_angle

    @phi.setter
    def phi(self, value):
        self.current_angle = self.voltage_angle - value

    @property
    def power_factor(self):
        """
        Returns the power factor with the chosen sign convention
        """
        return self.pf_sign_conversions[self.pf_sign_convention](self.phi)

    def process_phi_change(self, x_coord, y_coord):
        self.phi = np.arctan2(y_coord, x_coord)
        apparent_power = min(1., (y_coord ** 2 + x_coord ** 2) ** 0.5)
        self.current_rms = apparent_power / self.voltage_rms

    def refresh(self):
        """
        Update the waveforms based on changes to voltage, current or power angle
        """
        # Convert voltage/current rms values to phasors
        voltage_phasor = self.SQRT_TWO * self.voltage_rms * cmath.rect(1., self.voltage_angle)
        current_phasor = self.SQRT_TWO * self.current_rms * cmath.rect(1., self.current_angle)

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
