from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
from PySpice.Unit import *

from liberty.export import Pin

@dataclass
class PinTestBinding:
    """Associates a pin to test data, such as state"""
    pin: Pin
    state: str = '0'

    @property
    def direction(self) -> str:
        """Return pin state change direction (if applicable)"""
        if self.state.startswith(('01', 'z1')):
            return 'rise'
        elif self.state.startswith(('10', 'z0')):
            return 'fall'
        else:
            return None


class Harness:
    """Characterization parameters for one path through a cell
    
    A Harness defines characterization parameters from one input to one
    output of a standard cell circuit. The target input port and output
    port are defined by the value of test_vector passed to the
    constructor."""

    def __init__(self, target_cell, test_vector: list) -> None:
        """Create a new Harness.
        
        The key parameter here is test_vector. It describes the expected
        state of each input pin and output pin, as well as which input and
        output this Harness is testing. It should be formatted as a list of
        strings with N+M entries, where N is the number of input ports and
        M is the number of output ports in target_cell:

        [in1, ..., inN, out1, ..., outM]

        Each entry in test_vector is a string that represents the state of
        the corresponding I/O on the standard cell. For inputs, the values
        '0' and '1' represent nontarget input ports. These ports will be
        held stable with the corresponding logic values. Values of '01' or
        '10' indicate target input ports that are rising or falling
        respectively. The case is similar for outputs: '0' and '1' represent
        expected results for nontarget output ports, and '01' or '10'
        represent target outputs that are expected to fall or rise as the
        input changes.

        For example, a test vector for a single-input single-output inverter
        might look like this: ['01', '10'].
        Or a test vector for an AND gate with 2 inputs and a single output
        might look like: ['01', '1', '01'].

        Note that target_cell is only required for initialization checks,
        such as ensuring that test_vector correctly maps to the input and
        output pins of the cell under test. A Harness does not keep track of
        changes to target_cell. If target_cell is altered after the Harness
        was generated, a new Harness should be generated."""

        self._stable_in_ports = [] # input pins to hold stable
        self._nontarget_out_ports = [] # output pins that we aren't specifically evaluating
        self.results =  {} # nested dictionary of characterization results

        # Parse inputs from test vector
        # Test vector should be formatted like [in1, ..., inN, out1, ..., outM]
        num_inputs = len(target_cell.in_ports)
        num_outputs = len(target_cell.out_ports)
        input_test_vector = test_vector[0:num_inputs]
        output_test_vector = test_vector[num_inputs:num_inputs+num_outputs]

        # Get inputs from test vector
        for in_port, state in zip(target_cell.in_ports, input_test_vector):
            if len(state) > 1:
                self._target_in_port = PinTestBinding(in_port, state)
            else:
                self._stable_in_ports.append(PinTestBinding(in_port, state))

        # Get outputs from test vector
        for out_port, state in zip(target_cell.out_ports, output_test_vector):
            if len(state) > 1:
                self._target_out_port = PinTestBinding(out_port, state)
            else:
                self._nontarget_out_ports.append(PinTestBinding(out_port, state))
        if not self._target_out_port:
            raise ValueError(f'Unable to parse target output port from test vector {test_vector}')

        # Initialize results from target_cell input slopes and loads
        for in_slew in target_cell.in_slews:
            self.results[str(in_slew)] = {}
            for out_load in target_cell.out_loads:
                self.results[str(in_slew)][str(out_load)] = {}

    def __str__(self) -> str:
        """Return str(self)"""
        lines = [f'Arc Under Test: {self.arc_str()}']
        if self.stable_in_ports:
            lines.append('    Stable Input Ports:')
            for in_port in self.stable_in_ports:
                lines.append(f'        {in_port.pin.name}: {in_port.state}')
        if self.nontarget_out_ports:
            lines.append('    Nontarget Output Ports:')
            for out_port in self.nontarget_out_ports:
                lines.append(f'        {out_port.pin.name}: {out_port.state}')
        # TODO: Display results if available
        return '\n'.join(lines)

    def short_str(self):
        """Create an abbreviated string for the test vector represented by this harness"""
        # TODO: Replace this with a method that generates the test vector string (if possible)
        harness_str = f'{self.target_in_port.pin.name}={self.target_in_port.state}'
        for in_port in self.stable_in_ports:
            harness_str += f' {in_port.pin.name}={in_port.state}'
        harness_str += f' {self.target_out_port.pin.name}={self.target_out_port.state}'
        for out_port in self.nontarget_out_ports:
            harness_str += f' {out_port.pin.name}={out_port.state}'
        return harness_str

    def arc_str(self):
        """Return a string representing the test arc"""
        return f'{self.target_in_port.pin.name} ({self.in_direction}) -> {self.target_out_port.pin.name} ({self.out_direction})'

    @property
    def target_in_port(self) -> str:
        """Return target input port"""
        return self._target_in_port

    @property
    def stable_in_ports(self) -> list:
        """Return list of stable input ports"""
        return self._stable_in_ports

    @property
    def target_out_port(self) -> str:
        """Return target output ports"""
        return self._target_out_port

    @property
    def nontarget_out_ports(self) -> list:
        """Return list of nontarget output ports"""
        return self._nontarget_out_ports

    @property
    def in_direction(self) -> str:
        """Return target_in_port.direction"""
        return self.target_in_port.direction

    @property
    def out_direction(self) -> str:
        """Return target_out_port.direction"""
        return self.target_out_port.direction

    def average_propagation_delay(self):
        """Calculates the average propagation delay over all trials"""
        # TODO: Usually we want longest prop delay instead of average
        total_delay = 0.0 @ u_s
        n = 0
        for slope in self.results.keys():
            for load in self.results[slope].keys():
                total_delay += self.results[slope][load]['prop_in_out'] @ u_s
                n += 1
        return total_delay / n

    def _calc_internal_energy(self, slew: str, load: str, energy_meas_high_threshold_voltage: float):
        """Calculates internal energy for a particular slope/load combination"""
        # Fetch calculation parameters, using units to validate calculation
        slew = str(slew)
        load = str(load)
        t_start = self.results[slew][load]['t_energy_start'] @ u_s
        t_end = self.results[slew][load]['t_energy_end'] @ u_s
        q_vdd_dyn = self.results[slew][load]['q_vdd_dyn'] @ u_C
        q_vss_dyn = self.results[slew][load]['q_vss_dyn'] @ u_C
        i_vdd_leak = abs(self.results[slew][load]['i_vdd_leak']) @ u_A
        i_vss_leak = abs(self.results[slew][load]['i_vss_leak']) @ u_A
        # Perform the calculation
        time_delta = (t_end - t_start)
        avg_current = ((i_vdd_leak + i_vss_leak) / 2)
        internal_charge = min(abs(q_vss_dyn), abs(q_vdd_dyn)) - time_delta * avg_current
        return internal_charge * (energy_meas_high_threshold_voltage @ u_V)


class CombinationalHarness (Harness):
    """A CombinationalHarness captures configuration for testing a CombinationalCell."""
    def __init__(self, target_cell, test_vector) -> None:
        """Create a new CombinationalHarness."""
        super().__init__(target_cell, test_vector)
        # Error if we don't have a target input port
        if not self._target_in_port:
            raise ValueError(f'Unable to parse target input port from test vector {test_vector}')

    def plot_energy(self, settings, slews, loads, cell_name):
        """Plot energy vs slew rate vs fanout"""
        # TODO: Consider moving this to Pin, as all the data is eventually stored there anyways
        figure = plt.figure()
        figure.suptitle(f'Cell {cell_name} | Arc: {self.arc_str()}')

        ax = figure.add_subplot(projection='3d')
        ax.set_proj_type('ortho')

        energy_data = []
        for slew in slews:
            energy_row = []
            for load in loads:
                energy = self._calc_internal_energy(slew, load, settings.energy_meas_high_threshold_voltage())
                energy_row.append(float(energy.convert(settings.units.energy.prefixed_unit).value))
            energy_data.append(energy_row)

        # Expand x and y vectors to 2d arrays
        x_data = np.repeat(np.expand_dims(slews, 1), len(loads), 1)
        y_data = np.swapaxes(np.repeat(np.expand_dims(loads, 1), len(slews), 1), 0, 1)

        # Plot energy data
        ax.plot_surface(x_data, y_data, np.asarray(energy_data), cmap='viridis', label='Energy')
        ax.set(xlabel=f'Slew Rate [{str(settings.units.time.prefixed_unit)}]',
               ylabel=f'Fanout [{str(settings.units.capacitance.prefixed_unit)}]',
               zlabel=f'Energy [{str(settings.units.energy.prefixed_unit)}]',
               title='Energy vs. Slew Rate vs. Fanout')


class SequentialHarness (Harness):
    def __init__(self, target_cell, test_vector: list) -> None:
        # Parse internal storage states, clock, set, and reset out of test vector
        # For sequential harnesses, test vectors are in the format:
        # [clk, set, reset, flop1, ..., flopK, in1, ..., inN, out1, ..., outM]
        # Note that set and reset are optional, but must be provided if present
        # on the target cell
        self.set = None
        self.reset = None
        self.flops = []
        self.flop_states = []
        self.clock = PinTestBinding(target_cell.clock, test_vector.pop(0))
        # Set up Reset
        if target_cell.reset:
            self.reset = PinTestBinding(target_cell.reset, test_vector.pop(0))
            if len(self.reset.state) > 1:
                self._target_in_port = self.reset
        # Set up Set
        if target_cell.set:
            self.set = PinTestBinding(target_cell.set, test_vector.pop(0))
            if len(self.set.state) > 1:
                self._target_in_port = self.set
        # Set up flop internal states
        for flop in target_cell.flops:
            self.flops.append(flop)
            self.flop_states.append(test_vector.pop(0))
        super().__init__(target_cell, test_vector)

    def short_str(self):
        harness_str = f'{self.clock.pin.name}={self.clock.state} {super().short_str()}'
        if self.set:
            harness_str += f' {self.set.pin.name}={self.set.state}'
        if self.reset:
            harness_str += f' {self.reset.pin.name}={self.reset.state}'
        return harness_str

    @property
    def set_direction(self) -> str:
        if not self.set:
            return None
        return self.set.direction

    @property
    def reset_direction(self) -> str:
        if not self.reset:
            return None
        return self.reset.direction
    
    def invert_set_reset(self):
        self.set.state = self.set.state[::-1] if self.set.state else None
        self.reset.state = self.reset.state[::-1] if self.reset.state else None

    @property
    def timing_sense_constraint(self) -> str:
        # TODO: Check that this is correct
        return f'{self.in_direction}_constraint'

    def _timing_type_with_mode(self, mode) -> str:
        # Determine from target input and direction
        if self.set_direction or self.reset_direction:
            # We're targeting set or reset
            if mode == 'recovery':
                if self.in_direction == 'rise':
                    return f'{mode}_rising'
                else:
                    return f'{mode}_falling'
            elif mode == 'removal':
                if self.in_direction == 'rise':
                    return f'{mode}_falling'
                else:
                    return f'{mode}_rising'
            else:
                return None
        elif not self.target_in_port.pin.name in [*self.flops]:
            # We're targeting an input port
            if mode == 'clock':
                if self.clock.state == '0101':
                    return 'falling_edge'
                else:
                    return 'rising_edge'
            elif mode in ['hold', 'setup']:
                if self.in_direction == 'rise':
                    return f'{mode}_rising'
                else:
                    return f'{mode}_falling'
        # If we get here, most likely the harness isn't configured correctly
        raise ValueError(f'Unable to determine timing type for mode "{mode}"')

    @property
    def timing_type_hold(self) -> str:
        return self._timing_type_with_mode('hold')

    @property
    def timing_type_setup(self) -> str:
        return self._timing_type_with_mode('setup')
    
    @property
    def timing_type_recovery(self) -> str:
        return self._timing_type_with_mode('recovery')
    
    @property
    def timing_type_removal(self) -> str:
        return self._timing_type_with_mode('removal')
    
    @property
    def timing_type_clock(self) -> str:
        return self._timing_type_with_mode('clock')
    
    @property
    def timing_when(self) -> str:
        if self.in_direction == 'rise':
            return self.target_in_port
        else:
            return f'!{self.target_in_port}'

    def plot_energy(self, settings, slews, loads, cell_name):
        pass

# Utilities for working with Harnesses
def filter_harnesses_by_ports(harness_list: list, in_port, out_port) -> list:
    """Finds harnesses in harness_list which target in_port and out_port"""
    return [harness for harness in harness_list 
            if harness.target_in_port.pin == in_port
            and harness.target_out_port.pin == out_port]

def find_harness_by_arc(harness_list: list, in_port, out_port, out_direction) -> Harness:
    harnesses = [harness for harness in filter_harnesses_by_ports(harness_list, in_port, out_port) if harness.out_direction == out_direction]
    if len(harnesses) > 1:
        raise LookupError('Multiple harnesses present in harness_list with the specified arc!')
    elif len(harnesses) < 1:
        raise LookupError('No harnesses present in harness_list with the specified arc!')
    return harnesses[0]

def check_timing_sense(harness_list: list):
    """Checks that all CombinationalHarnesses in harness_list have the same unateness."""
    for harness in harness_list:
        if not harness.timing_sense == harness_list[0].timing_sense:
            return "non_unate"
    return harness_list[0].timing_sense
