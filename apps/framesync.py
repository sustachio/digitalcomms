import numpy as np
import adi
import matplotlib.pyplot as plt
from scipy import signal
import time
from apps.app_parent import App

fs = 1e6
Nsymbols = 10
cycles_per_symbol = 10 
preamble_length = 5

class FrameSync(App):
    def __init__(self, sdrman, gui):
        super().__init__(sdrman, gui)

        self.preamble_symbols = np.random.randint(0, 4, preamble_length)

        self.iq_ax            = self.new_plot("rx", "Raw I/Q", -100, 100)
        self.constellation_ax = self.new_plot("rx", "I/Q Constellation", -100, 100)
        self.frame_iq_ax      = self.new_plot("rx", "Frame I/Q", -100, 100)
        self.tx_frame_iq_ax   = self.new_plot("tx", "Frame I/Q", -3, 3)
        self.tx_fft_ax        = self.new_plot("tx", "FFT", -30, 0)


    def start(self):
        self.reset_plots()

        self.sdrman.rx_buffer_size = 10000
        self.sdrman.rebuild_rx_buffer()

        self.tx()

        # clear buffer
        for i in range(10):
            self.sdrman.sdr.rx()

        t = np.arange(self.sdrman.rx_buffer_size)/fs
        samples = self.sdrman.sdr.rx() * np.exp(-2.0j*np.pi*5000*t)
        #samples_interpolated = signal.resample_poly(samples, 16, 1)

        # preamble detection
        correlation = signal.correlate(samples, self.generate_samples(self.preamble_symbols), mode="valid")
        correlation = abs(correlation)
        correlation = correlation / (max(correlation)) * 60

        frame_start = np.argmax(correlation)
        frame = samples[frame_start:frame_start+(Nsymbols+preamble_length)*cycles_per_symbol]


        self.stop_tx()

        self.iq_ax.plot(np.arange(len(samples)), samples.real)
        self.iq_ax.plot(np.arange(len(samples)), samples.imag)
        self.iq_ax.plot(np.arange(len(correlation)), np.abs(correlation))

        self.frame_iq_ax.plot(np.arange(len(frame)), frame.real)
        self.frame_iq_ax.plot(np.arange(len(frame)), frame.imag)

        self.constellation_ax.scatter(samples.real, samples.imag)

        self.draw_plots()

    def generate_samples(self, symbols):
        symbols = np.repeat(symbols, cycles_per_symbol)
        samples = np.exp(1j*symbols * np.pi/2 + np.pi/4)

        return samples

    def tx(self):
        self.sdrman.rebuild_tx_buffer()

        symbols =  np.random.randint(0, 4, Nsymbols)
        symbols = np.concatenate((self.preamble_symbols, symbols))

        pad_len = 3000
        samples = self.generate_samples(symbols)

        self.tx_frame_iq_ax.plot(np.arange(len(samples)), samples.real)
        self.tx_frame_iq_ax.plot(np.arange(len(samples)), samples.imag)

        samples = np.pad(samples, pad_len)
        t = np.arange(len(symbols) * cycles_per_symbol + 2*pad_len)/fs - pad_len/fs
        samples *= 0.5*np.exp(2.0j*np.pi*5000*t)
        samples *= 2**14

        # plot fft
        psd = np.abs(np.fft.fftshift(np.fft.fft(samples/(2**14))))**2
        psd_dB = 10*np.log10(psd)
        fft_f = np.linspace(fs/-2, fs/2, len(psd_dB))
        psd_dB -= np.max(psd_dB)

        self.tx_fft_ax.plot(fft_f, psd_dB)
        #self.tx_fft_ax.plot(np.arange(len(samples)), samples)

        self.sdrman.cyclic_tx(samples)

    def stop_tx(self):
        self.sdrman.stop_cyclic_tx()

