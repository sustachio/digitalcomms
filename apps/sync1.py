import numpy as np
import adi
import matplotlib.pyplot as plt
from scipy import signal
import time

fs = 1e6
cycles_per_symbol = 10 

class Sync1():
    def __init__(self, sdrman, gui):
        self.sdrman = sdrman
        self.gui = gui

        self.a = 0

        self.running = False

        self.lines = [] # to clear plots

        self.iq_fig, self.iq_ax = plt.subplots(figsize=(3, 3))
        self.iq_ax.grid(True)
        self.iq_ax.set_ylim(-100,100)
        self.iq_ax.set_title("Sync 1: Raw I/Q Data vs. Time")

        self.constellation_fig, self.constellation_ax = plt.subplots(figsize=(3, 3))
        self.constellation_ax.grid(True)
        self.constellation_ax.set_ylim(-100,100)
        self.constellation_ax.set_title("Sync 1: Raw I/Q Constellation")

        self.tx_fft_fig, self.tx_fft_ax = plt.subplots(figsize=(3,3))
        self.tx_fft_ax.grid(True)
        self.tx_fft_ax.set_ylim(-30,0)
        self.tx_fft_ax.set_title("Sync 1: FFT")

        self.axs = [self.iq_ax, self.constellation_ax, self.tx_fft_ax]

    def time_sync(self, samples, resample_ratio):
        """
        mu = 0 # initial phase estimate
        out = np.zeros(int(len(samples)/resample_ratio), dtype=np.complex64)
        out_rail = np.zeros(len(out), dtype=np.complex64)
        i_in = 0 # current sample looking at input
        i_out = 2 # two left are 0
        while i_out < len(out) and i_in+16 < len(samples):
            print(i_in)
            output_symbol = samples[i_in*resample_ratio + int(mu*resample_ratio)] 
            out[i_out] = output_symbol # symbol guess
            out_rail[i_out] = int(np.real(output_symbol) > 0) + 1j*int(np.imag(output_symbol) > 0)

            x = (out_rail[i_out] - out_rail[i_out-2]) * np.conj(out[i_out-1])
            y = (out[i_out] - out[i_out-2]) * np.conj(out_rail[i_out-1])

            mm_val = np.real(y - x)
            mu += cycles_per_symbol + 0.3*mm_val

            i_in += int(np.floor(mu))
            mu = mu - np.floor(mu) # remove integer part
            i_out += 1

        return  out[2:i_out]
        """
        sps = resample_ratio*cycles_per_symbol
        mu = 0 # initial estimate of phase of sample
        out = np.zeros(len(samples) + 10, dtype=np.complex64)
        out_rail = np.zeros(len(samples) + 10, dtype=np.complex64) # stores values, each iteration we need the previous 2 values plus current value
        i_in = 0 # input samples index
        i_out = 2 # output index (let first two outputs be 0)
        while i_out < len(samples) and i_in+16 < len(samples):
            out[i_out] = samples[i_in] # grab what we think is the "best" sample
            out_rail[i_out] = int(np.real(out[i_out]) > 0) + 1j*int(np.imag(out[i_out]) > 0)
            x = (out_rail[i_out] - out_rail[i_out-2]) * np.conj(out[i_out-1])
            y = (out[i_out] - out[i_out-2]) * np.conj(out_rail[i_out-1])
            mm_val = np.real(y - x)
            mu += sps + 0.3*mm_val
            i_in += int(np.floor(mu)) # round down to nearest int since we are using it as an index
            mu = mu - np.floor(mu) # remove the integer part of mu
            i_out += 1 # increment output index
        out = out[2:i_out] # remove the first two, and anything after i_out (that was never filled out)
        samples = out # only include this line if you want to connect this code snippet with the Costas Loop later on
        return samples


    def start(self):
        self.gui.clear_graphs()
        self.iq_axcanvas = self.gui.rx_graphs.add_plot(self.iq_fig)
        self.constellation_axcanvas = self.gui.rx_graphs.add_plot(self.constellation_fig)
        self.tx_fft_axcanvas = self.gui.tx_graphs.add_plot(self.tx_fft_fig)

        for ax in self.axs:
            ax.set_prop_cycle(None) # reset color cycle
            for line in list(ax.lines):
                line.remove()
            for collection in list(ax.collections):
                collection.remove()

        self.sdrman.rx_buffer_size = 1000
        self.sdrman.rebuild_rx_buffer()

        self.tx()

        # clear buffer
        for i in range(10):
            self.sdrman.sdr.rx()

        samples_set = []
        for _ in range(3):
            t = np.arange(1000)/fs
            samples = self.sdrman.sdr.rx() * np.exp(-2.0j*np.pi*5000*t)
            samples_interpolated = signal.resample_poly(samples, 16, 1)

            #samples_set.append(self.time_sync(samples_interpolated, 16))
            samples_set.append((samples))

        self.stop_tx()

        samples = samples_set[0]
        self.iq_ax.plot(np.arange(len(samples)), samples.real)
        self.iq_ax.plot(np.arange(len(samples)), samples.imag)

        for samples in samples_set:
            self.constellation_ax.scatter(samples.real, samples.imag)


        self.iq_axcanvas.draw()
        self.constellation_axcanvas.draw()


    def tx(self):
        if not self.tx_fft_axcanvas:
            self.tx_fft_axcanvas = self.gui.tx_graphs.add_plot(self.tx_fft_fig)

        self.sdrman.rebuild_tx_buffer()

        Nsymbols = 100

        symbols = np.random.randint(0, 4, Nsymbols)
        symbols = np.repeat(symbols, cycles_per_symbol)
        symbols = np.exp(1j*symbols * np.pi/2 + np.pi/4)

        t = np.arange(Nsymbols * cycles_per_symbol)/fs
        samples = symbols
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

