## IDEA: P angles seem to be off by exatly pi, subtract or figure out y


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
        signal = np.fft.ifft(freqs) * np.sqrt(self.K)
        
        if self.CP > 0:
            signal = np.hstack([signal[-self.CP:], signal])

        return signal

    def demodulate(self, samples):
        assert(len(samples) == self.K)

        offset = int((self.K-self.Kon)/2)
        freqs = np.fft.fft(samples)
        #freqs = freqs[offset : offset + self.Kon]
        #freqs = np.fft.fftshift(freqs)

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

        self.iq_ax            = self.new_plot("rx", "Raw I/Q", ybounds=(-2, 2))
        self.frame_iq_ax      = self.new_plot("rx", "Frame I/Q", ybounds=(-np.pi, np.pi))
        self.frame_angle_ax   = self.new_plot("rx", "Frame Angle", ybounds=(-np.pi, np.pi))
        self.tx_frame_iq_ax   = self.new_plot("tx", "Frame I/Q", ybounds=(-3, 3))
        self.tx_fft_ax        = self.new_plot("tx", "FFT", ybounds=(-30, 0))

        self.ofdm = OFDM(1024, 600, 128)

    def start(self):
        self.reset_plots()

        self.sdrplusman.rx_buffer_size = 100000
        self.sdrplusman.rebuild_rx_buffer()

        self.tx()

        # clear buffer
        for i in range(10):
            self.sdrplusman.sdr.rx()

        t = np.arange(self.sdrplusman.rx_buffer_size)/fs
        samples = self.sdrplusman.sdr.rx()
        samples = samples * np.exp(-2.0j*np.pi*3000*t)

        # normalize
        samples /= (np.percentile(np.abs(samples), 99) + 1e-9)

        self.stop_tx()

        # calculate frame start
        #self.iq_ax.plot(np.arange(len(samples)), (samples.imag))

        metric, P = self.calc_metric(samples)
        sync = self.sync_from_metric(metric)

        start_inds = np.flatnonzero(sync)
        frame_start = start_inds[1]

        self.iq_ax.plot(np.arange(len(metric)), np.angle(P), label="∠P")
        self.iq_ax.plot(np.arange(len(samples)), (samples.real), label="real(s)")
        self.iq_ax.axvline(x=frame_start, color='red', label="frame start")
        #self.iq_ax.plot(np.arange(len(metric)), metric)
        #self.iq_ax.plot(np.arange(len(sync)), sync)

        # extract frames

        full_frame   = samples[frame_start : frame_start+(self.ofdm.K+self.ofdm.CP)*11]
        full_frame_P = P[frame_start : frame_start+(self.ofdm.K+self.ofdm.CP)*11]
        data_frame = samples[frame_start+self.ofdm.K+self.ofdm.CP : frame_start+(self.ofdm.K+self.ofdm.CP)*11]
        full_frame /= (np.percentile(np.abs(full_frame), 99) + 1e-9)
        data_frame /= (np.percentile(np.abs(full_frame), 99) + 1e-9)

        self.frame_iq_ax.plot(np.arange(len(full_frame)), np.abs(full_frame), label="|s|")
        self.frame_iq_ax.plot(np.arange(len(full_frame)), np.angle(full_frame_P), label="∠P")


        self.frame_angle_ax.plot(np.arange(len(data_frame)), np.angle(data_frame), label="s_θ initial")


        #self.frame_iq_ax.plot(np.arange(len(frame)), np.angle(frame) / np.pi)

        # CFO correction
        #offset = np.angle(P[frame_start])/(np.pi * self.ofdm.K)
        offset = np.angle(P[frame_start])/(np.pi * self.ofdm.K)
        cfo_correction = np.exp(2.0j * np.pi * offset * np.arange(len(data_frame)))
        print("estimated offset: ", offset * fs)

        data_frame = data_frame * cfo_correction

        self.frame_angle_ax.plot(np.arange(len(data_frame)), np.angle(cfo_correction)/ (np.pi), label="θ estimate")
        #self.frame_angle_ax.axhline(y=(np.angle(P[frame_start]) / (np.pi)), color='red')

        # rough phase correction
        phase = np.average(data_frame)
        phase = phase / (np.abs(phase) + 1e-9)
        data_frame = data_frame * np.conj(phase)

        self.frame_angle_ax.plot(np.arange(len(data_frame)), np.angle(data_frame), label="s_θ corrected")

        #self.frame_iq_ax.plot(np.arange(len(frame)), frame.real)
        #self.frame_iq_ax.plot(np.arange(len(frame)), frame.imag)

        # demodulate frame
        #frame_demod = self.ofdm.demodulate(frame)
        #frame_demod = frame_demod/np.max(np.abs(frame_demod))
        ##self.constellation_ax.scatter(frame_demod.real, frame_demod.imag)

        self.frame_iq_ax.plot(np.arange(len(data_frame)) + self.ofdm.CP + self.ofdm.K, data_frame.real, label="real(s)")
        self.frame_iq_ax.plot(np.arange(len(data_frame)) + self.ofdm.CP + self.ofdm.K, data_frame.imag, label="imag(s)")

        self.frame_angle_ax.legend()
        self.frame_iq_ax.legend()
        self.iq_ax.legend()
        self.draw_plots()

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
        P = P / np.max(np.abs(P) + 1e-9)
        R = np.abs(R) / np.max(np.abs(R) + 1e-9)

        return metric, P

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
        cox_freqs[1::2] = 0
        return self.ofdm.modulate(cox_freqs)

    def tx(self):
        txnullpad = 10000

        self.sdrman.rebuild_tx_buffer()
        
        preamble = self.cox_preamble()
        samples = preamble

        #data_freqs = np.zeros(self.ofdm.Kon, dtype=complex)
        #data_freqs = self.ofdm.random_4psk()
        #data_freqs[100] = 1.0
        #data = self.ofdm.modulate(data_freqs)
        for i in range(10):
            data = np.repeat([1+1j, 1-1j, -1+1j, -1-1j][i%4], self.ofdm.K + self.ofdm.CP)
            samples = np.hstack([samples, data])

        samples = np.pad(samples, txnullpad)

        t = np.arange(len(samples))/fs
        samples *= np.exp(2.0j*np.pi*3000*t)
        metric, P = self.calc_metric(samples)

        #samples += (np.random.rand(len(samples)) + 1j*np.random.rand(len(samples))-.5-.5j) * 0.5

        #self.tx_frame_iq_ax.plot(np.arange(len(samples)), np.abs(samples))
        self.tx_frame_iq_ax.plot(np.arange(len(samples)), (samples.real))
        self.tx_frame_iq_ax.plot(np.arange(len(samples)), (samples.imag))
        self.tx_frame_iq_ax.plot(np.arange(len(P)), (np.angle(P)))

        self.tx_frame_iq_ax.axvline(x=txnullpad, color='orange') # CP start
        self.tx_frame_iq_ax.axvline(x=txnullpad+self.ofdm.CP, color='orange') # preamble start
        self.tx_frame_iq_ax.axvline(x=txnullpad+self.ofdm.CP+self.ofdm.K, color='orange') # preamble end

        # plot fft
        fft_f, psd_dB = self.fft_graph(samples, fs)
        self.tx_fft_ax.plot(fft_f, psd_dB)

        samples *= 2**13
        t = np.arange(len(samples))/fs
        self.sdrman.cyclic_tx(samples)

    def stop_tx(self):
        self.sdrman.stop_cyclic_tx()