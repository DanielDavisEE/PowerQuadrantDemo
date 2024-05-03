"""
Model component of the GUI
"""

import cmath
import logging
import tkinter as tk

import numpy as np
import pandas as pd

SQRT_TWO = 2 ** 0.5


def create_phasor(amplitude, angle):
    return amplitude * cmath.rect(1., angle)


def phi_to_pf(phi, sign_convention):
    """
    Convert the power angle to power factor following the selected sign convention
    """
    pf = np.cos(phi)
    if sign_convention == 'EEI':
        pf *= -np.sign(np.sin(phi))
    return pf


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


class ModelledWaveforms:
    MIN_TIME, MAX_TIME = -10, 30
    PERIOD = 20
    OMEGA = 2 * np.pi / PERIOD

    def __init__(self, rms_voltage_phasor, rms_current_phasor):
        self.waveforms = pd.DataFrame([], columns=['time', 'phase', 'voltage', 'current',
                                                   'active_current', 'reactive_current', 'summed_current',
                                                   'active_power', 'reactive_power', 'apparent_power',
                                                   ])

        self.waveforms['time'] = np.linspace(self.MIN_TIME, self.MAX_TIME, 100)
        self.waveforms['phase'] = np.exp(1j * self.OMEGA * self.waveforms['time'])

        self.refresh(rms_voltage_phasor, rms_current_phasor)

    def refresh(self, rms_voltage_phasor, rms_current_phasor):
        voltage_phasor = SQRT_TWO * rms_voltage_phasor
        current_phasor = SQRT_TWO * rms_current_phasor

        self.waveforms['voltage'] = np.real(voltage_phasor * self.waveforms['phase'])
        self.waveforms['current'] = np.real(current_phasor * self.waveforms['phase'])

        self.waveforms['active_current'] = np.real(np.real(current_phasor) * self.waveforms['phase'])
        self.waveforms['reactive_current'] = np.real(np.imag(current_phasor) * self.waveforms['phase'] * 1j)
        self.waveforms['summed_current'] = self.waveforms['active_current'] + self.waveforms['reactive_current']

        self.waveforms['active_power'] = self.waveforms['voltage'] * self.waveforms['active_current']
        self.waveforms['reactive_power'] = self.waveforms['voltage'] * self.waveforms['reactive_current']
        self.waveforms['apparent_power'] = self.waveforms['voltage'] * self.waveforms['current']


class PowerStateVariables:
    def __init__(self, root):
        self.pf_sign_convention = tk.StringVar(name='SignConvention', value='EEI')

        # State variables
        self.apparent_power = VersatileVar(root, name='S', value=1.)
        self.power_angle = VersatileVar(root, name='Phi', value=0., width=5)
        self.voltage_rms = VersatileVar(root, name='Vrms', value=1.)
        self.voltage_angle = VersatileVar(root, name='VoltageTheta', value=0.)
        self.current_rms = VersatileVar(root, name='Irms', value=1.)
        self.current_angle = VersatileVar(root, name='CurrentTheta', value=0.)
        self.impedance = VersatileVar(root, name='Z', value=1.)
        # Impedance doesn't have an angle as it is equal to power angle

        # Derived variables
        self.cos_phi = VersatileVar(root, name='cos(φ)', value=1.)
        self.power_factor = VersatileVar(root, name='PF', value=1.)
        self.active_power = VersatileVar(root, name='R', value=1.)
        self.reactive_power = VersatileVar(root, name='Q', value=0.)

    @property
    def voltage_phasor(self):
        return create_phasor(self.voltage_rms.get(), self.voltage_angle.get())

    @voltage_phasor.setter
    def voltage_phasor(self, phasor):
        self.voltage_rms.set(np.abs(phasor))
        self.voltage_angle.set(np.angle(phasor))

    @property
    def current_phasor(self):
        return create_phasor(self.current_rms.get(), self.current_angle.get())

    @current_phasor.setter
    def current_phasor(self, phasor):
        self.current_rms.set(np.abs(phasor))
        self.current_angle.set(np.angle(phasor))

    @property
    def power_phasor(self):
        return create_phasor(self.apparent_power.get(), self.power_angle.get())

    @power_phasor.setter
    def power_phasor(self, phasor):
        self.apparent_power.set(np.abs(phasor))
        self.power_angle.set(np.angle(phasor))

    @property
    def impedance_phasor(self):
        return create_phasor(self.impedance.get(), self.power_angle.get())

    @impedance_phasor.setter
    def impedance_phasor(self, phasor):
        self.impedance.set(np.abs(phasor))
        self.power_angle.set(np.angle(phasor))

    def refresh(self):
        """
        Update the waveforms based on changes to voltage, current or power angle
        """
        # Update dependent state variables
        self.current_rms.set(self.apparent_power.get() / self.voltage_rms.get())
        self.current_angle.set(self.voltage_angle.get() - self.power_angle.get())
        self.cos_phi.set(np.cos(self.power_angle.get()))
        self.power_factor.set(phi_to_pf(self.power_angle.get(), self.pf_sign_convention.get()))
        self.active_power.set(self.apparent_power.get() * np.cos(self.power_angle.get()))
        self.reactive_power.set(self.apparent_power.get() * np.sin(self.power_angle.get()))


class Model:
    """
    The model component of the MVC gui model
    """
    DIMENSIONS = 6, 9

    def __init__(self, root):
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.debug('Running __init__')

        self.state_count = tk.IntVar(root, name='StateCount', value=0)

        self._state_variables = PowerStateVariables(root)
        self._waveforms = ModelledWaveforms(self._state_variables.voltage_phasor,
                                            self._state_variables.current_phasor)

        # Bind the two input variables to the model refresh method
        self._state_variables.power_angle.trace_add('write', lambda *_: self.refresh())
        self._state_variables.pf_sign_convention.trace_add('write', lambda *_: self.refresh())

        self.refresh()

    @property
    def waveforms(self):
        """
        Return a 'read-only' copy of the waveforms for a view to use
        """
        return self._waveforms.waveforms.copy()

    def process_power_phasor_change(self, x_coord, y_coord):
        """
        Takes the coordinates of a quadrant graph input and updates power_angle accordingly
        """
        new_phasor = create_phasor(min(1., (x_coord ** 2 + y_coord ** 2) ** 0.5), np.arctan2(y_coord, x_coord))
        self._state_variables.power_phasor = new_phasor

    def refresh(self):
        """
        Update the waveforms based on changes to voltage, current or power angle
        """
        self._state_variables.refresh()
        self._waveforms.refresh(self._state_variables.voltage_phasor,
                                self._state_variables.current_phasor)

        # Increment the state count variable to indicate the model has updated
        self.state_count.set((self.state_count.get() + 1) % 0xff)
