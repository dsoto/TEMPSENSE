# The MIT License (MIT)
#
# Copyright (c) 2017 Radomir Dopieralski for Adafruit Industries.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
``adafruit_max31855``
===========================

This is a CircuitPython driver for the Maxim Integrated MAX31855 thermocouple
amplifier module.

* Author(s): Radomir Dopieralski

Implementation Notes
--------------------

**Hardware:**

* Adafruit `MAX31855 Thermocouple Amplifier Breakout
  <https://www.adafruit.com/product/269>`_ (Product ID: 269)

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the ESP8622 and M0-based boards:
  https://github.com/adafruit/circuitpython/releases
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""
import math
try:
    import struct
except ImportError:
    import ustruct as struct

from adafruit_bus_device.spi_device import SPIDevice

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_MAX31855.git"

class MAX31855:
    """
    Driver for the MAX31855 thermocouple amplifier.
    """

    def __init__(self, spi, cs):
        self.spi_device = SPIDevice(spi, cs)
        self.data = bytearray(4)

    def _read(self, internal=False):
        with self.spi_device as spi:
            spi.readinto(self.data)  #pylint: disable=no-member
        if self.data[3] & 0x01:
            raise RuntimeError("thermocouple not connected")
        if self.data[3] & 0x02:
            raise RuntimeError("short circuit to ground")
        if self.data[3] & 0x04:
            raise RuntimeError("short circuit to power")
        if self.data[1] & 0x01:
            raise RuntimeError("faulty reading")
        temp, refer = struct.unpack('>hh', self.data)
        refer >>= 4
        temp >>= 2
        if internal:
            return refer
        return temp

    @property
    def temperature(self):
        """Thermocouple temperature in degrees Celsius."""
        return self._read() / 4

    @property
    def reference_temperature(self):
        """Internal reference temperature in degrees Celsius."""
        return self._read(True) * 0.0625

    @property
    def temperature_NIST(self):
        """
        Thermocouple temperature in degrees Celsius, computed using
        raw voltages and NIST approximation for Type K, see:
        https://srdata.nist.gov/its90/download/type_k.tab
        """
        # pylint: disable=bad-whitespace, bad-continuation, invalid-name
        # temperature of remote thermocouple junction
        TR = self.temperature
        # temperature of device (cold junction)
        TAMB = self.reference_temperature
        # thermocouple voltage based on MAX31855's uV/degC for type K (table 1)
        VOUT = 0.041276 * (TR - TAMB)
        # cold junction equivalent thermocouple voltage
        if TAMB >= 0:
            VREF =(-0.176004136860E-01 +
                    0.389212049750E-01 * TAMB +
                    0.185587700320E-04 * math.pow(TAMB, 2) +
                   -0.994575928740E-07 * math.pow(TAMB, 3) +
                    0.318409457190E-09 * math.pow(TAMB, 4) +
                   -0.560728448890E-12 * math.pow(TAMB, 5) +
                    0.560750590590E-15 * math.pow(TAMB, 6) +
                   -0.320207200030E-18 * math.pow(TAMB, 7) +
                    0.971511471520E-22 * math.pow(TAMB, 8) +
                   -0.121047212750E-25 * math.pow(TAMB, 9) +
                    0.1185976 * math.exp(-0.1183432E-03 * math.pow(TAMB - 0.1269686E+03, 2)))
        else:
            VREF =( 0.394501280250E-01 * TAMB +
                    0.236223735980E-04 * math.pow(TAMB, 2) +
                   -0.328589067840E-06 * math.pow(TAMB, 3) +
                   -0.499048287770E-08 * math.pow(TAMB, 4) +
                   -0.675090591730E-10 * math.pow(TAMB, 5) +
                   -0.574103274280E-12 * math.pow(TAMB, 6) +
                   -0.310888728940E-14 * math.pow(TAMB, 7) +
                   -0.104516093650E-16 * math.pow(TAMB, 8) +
                   -0.198892668780E-19 * math.pow(TAMB, 9) +
                   -0.163226974860E-22 * math.pow(TAMB, 10))
        # total thermoelectric voltage
        VTOTAL = VOUT + VREF
        # determine coefficients
        # https://srdata.nist.gov/its90/type_k/kcoefficients_inverse.html
        if -5.891 <= VTOTAL <=0:
            DCOEF = (0.0000000E+00,
                     2.5173462E+01,
                    -1.1662878E+00,
                    -1.0833638E+00,
                    -8.9773540E-01,
                    -3.7342377E-01,
                    -8.6632643E-02,
                    -1.0450598E-02,
                    -5.1920577E-04)
        elif 0 < VTOTAL <= 20.644:
            DCOEF = (0.000000E+00,
                     2.508355E+01,
                     7.860106E-02,
                    -2.503131E-01,
                     8.315270E-02,
                    -1.228034E-02,
                     9.804036E-04,
                    -4.413030E-05,
                     1.057734E-06,
                    -1.052755E-08)
        elif 20.644 < VTOTAL <= 54.886:
            DCOEF = (-1.318058E+02,
                      4.830222E+01,
                     -1.646031E+00,
                      5.464731E-02,
                     -9.650715E-04,
                      8.802193E-06,
                     -3.110810E-08)
        else:
            raise RuntimeError("Total thermoelectric voltage out of range:{}".format(VTOTAL))
        # compute temperature
        TEMPERATURE = 0
        for n, c in enumerate(DCOEF):
            TEMPERATURE += c * math.pow(VTOTAL, n)
        return TEMPERATURE
