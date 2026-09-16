import numpy as np
import adi
import matplotlib.pyplot as plt
from scipy import signal
import time

fs = 1e6
cycles_per_symbol = 10 

class FrameSync():
    def __init__(self, sdrman, gui):
        self.sdrman = sdrman
        self.gui = gui

        self.preamble_symbols = np.random.randint(0, 4, 10)

        self.running = False

        self.lines = [] # to clear plots

        self.iq_fig, self.iq_ax = plt.subplots(figsize=(3, 3))
        self.iq_ax.grid(True)
        self.iq_ax.set_ylim(-100,100)
        self.iq_ax.set_title("Sync 1: Raw I/Q Data vs. Time")
        self.iq_axcanvas = None

        self.constellation_fig, self.constellation_ax = plt.subplots(figsize=(3, 3))
        self.constellation_ax.grid(True)
        self.constellation_ax.set_ylim(-100,100)
        self.constellation_ax.set_title("Sync 1: Raw I/Q Constellation")
        self.constellation_axcanvas = None

        self.tx_fft_fig, self.tx_fft_ax = plt.subplots(figsize=(3,3))
        self.tx_fft_ax.grid(True)
        self.tx_fft_ax.set_ylim(-30,0)
        self.tx_fft_ax.set_title("Sync 1: FFT")
        self.tx_fft_axcanvas = None

    

    def start(self):
        if not self.iq_axcanvas:
            self.iq_axcanvas = self.gui.rx_graphs.add_plot(self.iq_fig)
        if not self.constellation_axcanvas:
            self.constellation_axcanvas = self.gui.rx_graphs.add_plot(self.constellation_fig)

        self.sdrman.rx_buffer_size = 10000
        self.sdrman.rebuild_rx_buffer()

        self.tx()

        # clear buffer
        for i in range(10):
            self.sdrman.sdr.rx()

        t = np.arange(10000)/fs
        samples = self.sdrman.sdr.rx() * np.exp(-2.0j*np.pi*5000*t)

        correlation = signal.correlate(samples, self.generate_samples(self.preamble_symbols), mode="valid")
        correlation = abs(correlation)
        correlation = correlation / (max(correlation)) * 60
        #samples_interpolated = signal.resample_poly(samples, 16, 1)

        self.stop_tx()

        #for line in self.lines:
            #line.remove()
        self.lines = []

        self.lines.append(self.iq_ax.plot(np.arange(len(samples)), samples.real))
        self.lines.append(self.iq_ax.plot(np.arange(len(samples)), samples.imag))
        self.lines.append(self.iq_ax.plot(np.arange(len(correlation)), np.abs(correlation)))

        self.lines.append(self.constellation_ax.scatter(samples.real, samples.imag))

        self.iq_axcanvas.draw()
        self.constellation_axcanvas.draw()

    def generate_samples(self, symbols):
        symbols = np.repeat(symbols, cycles_per_symbol)
        samples = np.exp(1j*symbols * np.pi/2 + np.pi/4)

        return samples

    def tx(self):
        if not self.tx_fft_axcanvas:
            self.tx_fft_axcanvas = self.gui.tx_graphs.add_plot(self.tx_fft_fig)

        self.sdrman.rebuild_tx_buffer()

        Nsymbols = 100
        symbols =  np.random.randint(0, 4, Nsymbols)
        symbols = np.concatenate((self.preamble_symbols, symbols))

        pad_len = 3000
        samples = self.generate_samples(symbols)
        t = np.arange(len(symbols) * cycles_per_symbol + 2*pad_len)/fs - pad_len/fs
        samples = np.pad(samples, pad_len)
        samples *= 0.5*np.exp(2.0j*np.pi*5000*t)
        samples *= 2**14

        # plot fft
        psd = np.abs(np.fft.fftshift(np.fft.fft(samples/(2**14))))**2
        psd_dB = 10*np.log10(psd)
        fft_f = np.linspace(fs/-2, fs/2, len(psd_dB))
        psd_dB -= np.max(psd_dB)

        self.lines.append(self.tx_fft_ax.plot(fft_f, psd_dB))
        #self.lines.append(self.tx_fft_ax.plot(np.arange(len(samples)), samples))
        self.tx_fft_axcanvas.draw()

        self.sdrman.cyclic_tx(samples)

    def stop_tx(self):
        self.sdrman.stop_cyclic_tx()

