import numpy as np
import adi
import matplotlib.pyplot as plt

sample_rate = 1e6

class CWTest():
    def __init__(self, sdrman):
        self.sdrman = sdrman
        self.freq = 100e3

    def set_freq(self, freq):
        self.freq = float(freq)

    def tx(self):
        self.sdrman.rebuild_tx_buffer()

        N = 10000
        t = np.arange(N)/sample_rate
        samples = 0.5*np.exp(2.0j*np.pi*self.freq*t)
        samples *= 2**14

        self.sdrman.cyclic_tx(samples)

    def stop_tx(self):
        self.sdrman.stop_cyclic_tx()

