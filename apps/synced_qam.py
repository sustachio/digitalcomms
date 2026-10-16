import numpy as np
import adi
import matplotlib.pyplot as plt
from scipy import signal, fft
import time
from apps.app_parent import *

fs = 1e6

class OFDM:
    def __init__(self, K, Kon, CP): # carriers, carries enabled, cyclic prefix
        self.K = K
        self.Kon = Kon
        self.CP = CP

    def modulate(self, qam): # center of qam is 0hz
        assert(len(qam) == self.Kon)

        offset = int((self.K-self.Kon)/2)
        freqs = np.pad(qam, (offset + (1 if (self.K-self.Kon)%2==1 else 0), offset))
        freqs = np.fft.fftshift(freqs)
        signal = np.fft.ifft(freqs) * np.sqrt(self.K)
        
        if self.CP > 0:
            signal = np.hstack([signal[-self.CP:], signal])

        return signal

    def demodulate(self, samples):
        assert(len(samples) == self.K)

        offset = int((self.K-self.Kon)/2)
        freqs = np.fft.fft(samples)
        freqs[0:offset] = 0
        freqs[-(offset + (1 if (self.K-self.Kon)%2==1 else 0)):-1] = 0
        freqs[-1] = 0
        freqs = np.fft.fftshift(freqs)

        return freqs

    def random_4psk(self):
        qam = np.array([1+1j, 1-1j, -1+1j, -1-1j]) * np.sqrt(2)
        return np.random.choice(qam, size=self.Kon, replace=True)

    def random_qam(self):
        return (np.random.rand(self.Kon) + 1j*np.random.rand(self.Kon)) / np.sqrt(2)


class SyncedQAM(App):
    def __init__(self, sdrman, sdrplusman, gui):
        super().__init__(sdrman, sdrplusman, gui)
        self.name = "Synced QAM"
        self.description = "QAM modulation/demodualtion with schmidl&cox syncing and channel correction"
        self.gui_elements = [GUIButton("Start", self.start)]

        self.iq_ax            = self.new_plot("rx", "Raw I/Q", ybounds=(-100, 100))
        self.constellation_ax = self.new_plot("rx", "I/Q Constellation", ybounds=(-100, 100), xbounds=(-100,100))
        self.frame_iq_ax      = self.new_plot("rx", "Frame I/Q", ybounds=(-100, 100))
        self.tx_frame_iq_ax   = self.new_plot("tx", "Frame I/Q", ybounds=(-3, 3))
        self.tx_fft_ax        = self.new_plot("tx", "FFT", ybounds=(-30, 0))

        self.ofdm = OFDM(1024, 600, 128)

    def start(self):
        self.reset_plots()

        self.sdrman.rx_buffer_size = 100000
        self.sdrman.rebuild_rx_buffer()

        self.tx()

        # clear buffer
        for i in range(10):
            self.sdrman.sdr.rx()

        t = np.arange(self.sdrman.rx_buffer_size)/fs
        samples = self.sdrman.sdr.rx()

        self.stop_tx()

        self.iq_ax.plot(np.arange(len(samples)), np.abs(samples))
        self.iq_ax.plot(np.arange(len(samples)), (samples.real))

        metric = self.calc_metric(samples)
        sync = self.sync_from_metric(metric)

        # extract frames
        start_inds = np.flatnonzero(sync)
        i = start_inds[1]
        frame = samples[i+self.ofdm.K+self.ofdm.CP : i+2*self.ofdm.K+self.ofdm.CP]

        frame_demod = self.ofdm.demodulate(frame)
        frame_demod = frame_demod/np.max(np.abs(frame_demod)) * 50

        self.frame_iq_ax.plot(np.arange(len(frame_demod)), frame_demod.real)
        self.frame_iq_ax.plot(np.arange(len(frame_demod)), frame_demod.imag)
        #self.frame_iq_ax.plot(np.arange(len(frame)), frame.real)
        # plot
        metric *= 50
        sync *= 50
        self.iq_ax.plot(np.arange(len(metric)), metric)
        self.iq_ax.plot(np.arange(len(sync)), sync)
        self.constellation_ax.scatter(frame_demod.real, frame_demod.imag)

        self.draw_plots()

    def generate_samples(self, symbols):
        symbols = np.repeat(symbols, cycles_per_symbol)
        samples = np.exp(1j*symbols * np.pi/2 + np.pi/4)

        return samples

    def calc_metric(self, samples):
        L = self.ofdm.K//2
        P = samples * (np.pad(samples, (0,L))[L:]).conj() # x[n] * x[n-L].conj()
        P = np.convolve(P, np.ones(L), mode="valid") # sumnation
        R = np.convolve(np.square(np.abs(samples)), np.ones(L), mode="valid") # sig strength
        R = np.pad(R, (0,L))[L:] # shift left L
        metric = (np.abs(np.square(P))) / (np.square(R) + 1e-9)

        # cutoff ends
        P = P[:-L]
        R = R[:-L]
        metric = metric[:-L]

        # normalize
        metric = np.abs(metric) / (np.percentile(np.abs(metric), 99) + 1e-9) # percintile instead of max to prevent outliers
        P = np.abs(P) / np.max(np.abs(P) + 1e-9)
        R = np.abs(R) / np.max(np.abs(R) + 1e-9)

        return metric

    def sync_from_metric(self, metric):
        metric = np.convolve(metric, np.ones(self.ofdm.CP)/self.ofdm.CP)
        diff = np.diff(metric)

        metric = ((diff[:-1] * diff[1:]) <= 0) * (metric[1:-1] > 0.5) * 1 # zero crossings in metric

        ignore_window = np.ones(self.ofdm.CP + self.ofdm.K + 2000)
        ignore_window[-1] = 0

        ignore = np.convolve(metric, ignore_window, mode="valid")
        ignore = np.pad(ignore, (self.ofdm.CP + self.ofdm.K + 2000, 0), mode="constant", constant_values=1)[:-1]
        metric = metric * (ignore == 0)

        return metric

    def cox_preamble(self):
        cox_freqs = self.ofdm.random_4psk()
        cox_freqs[::2] = 0
        return self.ofdm.modulate(cox_freqs)

    def tx(self):
        txnullpad = 10000

        self.sdrman.rebuild_tx_buffer()
        
        preamble = self.cox_preamble()

        t = np.arange(2000)/100
        data = np.exp(2.0j*np.pi*t)
        data += np.exp(2.0j*2*np.pi*t) * np.exp(1)
        data_freqs = np.zeros(self.ofdm.Kon, dtype=complex)
        data_freqs = self.ofdm.random_4psk()
        data_freqs[4] = 1.0j
        #data_freqs[7] = 1.0
        data = self.ofdm.modulate(data_freqs)
        samples = np.hstack([preamble, data])
        samples = np.pad(samples, txnullpad)

        #samples += (np.random.rand(len(samples)) + 1j*np.random.rand(len(samples))-.5-.5j) * 0.5

        #self.tx_frame_iq_ax.plot(np.arange(len(samples)), np.abs(samples))
        self.tx_frame_iq_ax.plot(np.arange(len(samples)), (samples.real))
        self.tx_frame_iq_ax.plot(np.arange(len(samples)), (samples.imag))

        self.tx_frame_iq_ax.axvline(x=txnullpad, color='orange') # CP start
        self.tx_frame_iq_ax.axvline(x=txnullpad+self.ofdm.CP, color='orange') # preamble start
        self.tx_frame_iq_ax.axvline(x=txnullpad+self.ofdm.CP+self.ofdm.K, color='orange') # preamble end

        # plot fft
        fft_f, psd_dB = self.fft_graph(samples, fs)
        self.tx_fft_ax.plot(fft_f, psd_dB)

        samples *= 2**13
        self.sdrman.cyclic_tx(samples)

    def stop_tx(self):
        self.sdrman.stop_cyclic_tx()