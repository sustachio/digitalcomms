import numpy as np
import adi
import matplotlib.pyplot as plt
import time

fs = 1e6

class Sync1():
    def __init__(self, sdrman, gui):
        self.sdrman = sdrman
        self.gui = gui

        self.a = 0
        self.iq_fig, self.iq_ax = plt.subplots(figsize=(3, 3))
        self.constellation_fig, self.constellation_ax = plt.subplots(figsize=(3, 3))

        self.running = False

    def start(self):
        self.iq_axcanvas = self.gui.rx_graphs.add_plot(self.iq_fig)
        self.iq_axcanvas = self.gui.rx_graphs.add_plot(self.constellation_fig)

        self.sdrman.rx_buffer_size = 10000
        self.sdrman.rebuild_rx_buffer()

        self.tx()

        # clear buffer
        for i in range(10):
            self.sdrman.sdr.rx()

        t = np.arange(10000)/fs
        samples = self.sdrman.sdr.rx() * np.exp(-2.0j*np.pi*5000*t)

        self.stop_tx()

        self.iq_ax.cla()
        self.iq_ax.plot(np.arange(len(samples)), samples.real)
        self.iq_ax.plot(np.arange(len(samples)), samples.imag)
        self.iq_ax.set_title("Plot! " + str(self.a))

        self.constellation_ax.cla()
        self.constellation_ax.scatter(samples.real, samples.imag)
        self.constellation_ax.set_title("Plot! " + str(self.a))

        self.iq_ax.grid(True)
        self.iq_ax.set_ylim(-100,100)
        self.constellation_ax.grid(True)
        self.constellation_ax.set_ylim(-100,100)

        self.iq_axcanvas.draw()


    def tx(self):
        self.sdrman.rebuild_tx_buffer()

        Nsymbols = 100
        cycles_per_symbol = 100

        symbols = np.random.randint(0, 4, Nsymbols)
        symbols = np.repeat(symbols, cycles_per_symbol)
        symbols = np.exp(1j*symbols * np.pi/2 + np.pi/4)

        t = np.arange(Nsymbols * cycles_per_symbol)/fs
        samples = symbols
        samples *= 0.5*np.exp(2.0j*np.pi*5000*t)
        samples *= 2**14

        self.sdrman.cyclic_tx(samples)

    def stop_tx(self):
        self.sdrman.stop_cyclic_tx()

