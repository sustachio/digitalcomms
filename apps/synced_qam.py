# ideas: find center of mass of preamble fft and determine offset from that
# interpolate fft peaks or something?
"""
mag = np.abs(fft)
# Find maximum FFT bin
i = np.argmax(mag)
# Number of points on either side of peak
n = 5
# Select points around peak
x = np.arange(i-n, i+n+1)
y = mag[x]
# Fit a parabola (2nd degree polynomial)
p = np.polyfit(x, y, 2)
# Find vertex
peak_bin = -p[1] / (2*p[0])
# Convert bin to frequency
f_peak = np.interp(peak_bin, np.arange(len(freq)), freq)
print(f_peak)
"""

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
        assert len(qam) == self.Kon

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

    def random_carriers_4psk(self):
        qam = np.array([1+1j, 1-1j, -1+1j, -1-1j]) * np.sqrt(2)
        return np.random.choice(qam, size=self.Kon, replace=True)





class SyncedQAM(App):
    def __init__(self, sdrman, sdrplusman, gui):
        super().__init__(sdrman, sdrplusman, gui)
        self.name = "Synced QAM"
        self.description = "QAM modulation/demodualtion with schmidl&cox syncing and channel correction"
        self.gui_elements = [GUIButton("Start", self.start)]

        self.iq_ax            = self.new_plot("rx", "Raw I/Q", ybounds=(-2, 2))
        self.frame_iq_ax      = self.new_plot("rx", "Frame I/Q", ybounds=(-np.pi, np.pi))
        self.frame_angle_ax   = self.new_plot("rx", "Frame Angle", ybounds=(-np.pi, np.pi))
        self.cfo_est_ax       = self.new_plot("rx", "CFO Coarse Bin Estimate", ybounds=(-.1, 1.1))
        self.tx_frame_iq_ax   = self.new_plot("tx", "Frame I/Q", ybounds=(-3, 3))
        self.tx_fft_ax        = self.new_plot("tx", "FFT", ybounds=(-30, 0))

        self.ofdm = OFDM(1024, 600, 128)
        #self.ofdm = OFDM(100, 40, 20)

        self.saved_cox_preamble = []

    def start(self):
        self.reset_plots()

        self.tx()
        samples = self.rx()
        self.stop_tx()

        # calculate frame start
        #self.iq_ax.plot(np.arange(len(samples)), (samples.imag))

        frame_start_inds, arg_P = self.frame_start_inds_and_arg_p(samples)
        frame_start = frame_start_inds[1]


        full_frame, cox_preamble, cfo_preamble, data_frames, full_data = self.extract_frame_parts(samples, frame_start, 10)
        #data_frame = np.hstack(data_frames)
        data_frame = full_data

        self.iq_ax.plot(np.arange(len(arg_P)), arg_P, label="∠P")
        self.iq_ax.plot(np.arange(len(samples)), (samples.real), label="real(s)")
        self.iq_ax.axvline(x=frame_start, color='red', label="frame start")

        self.frame_iq_ax.plot(np.arange(len(full_frame)), np.abs(full_frame), label="|s|")

        self.frame_angle_ax.plot(np.arange(len(data_frame)), np.angle(data_frame), label="s_θ initial")

        # coarse CFO correction
        fft_mag = np.abs(np.fft.fft(cfo_preamble))
        peak_bin = np.argmax(fft_mag)
        n = 5 # points on either side

        domain = np.arange(peak_bin-n, peak_bin+n+1)
        y = fft_mag[domain]
        y /= np.max(y)

        p = np.polyfit(domain, y, 2)
        peak_bin = -p[1] / (2*p[0]) # vertex
        coarse_offset = round((self.ofdm.K - self.ofdm.Kon) / 2 - peak_bin)

        fine_domain = np.arange(peak_bin-n,peak_bin+n+1,.1)
        self.cfo_est_ax.plot(domain, y, label="fft")
        self.cfo_est_ax.plot(fine_domain, p[0]*fine_domain**2+p[1]*fine_domain+p[2], label="est")
        self.cfo_est_ax.axvline(x=peak_bin, color='red', label="vertex")

        cfo_correction = np.exp(2.0j * np.pi * coarse_offset / self.ofdm.K * np.arange(len(data_frame)))
        print("coarse offset: ", coarse_offset * fs, "todo: find unit")

        # fine CFO correction
        fine_offset = arg_P[frame_start]/(np.pi * self.ofdm.K)
        cfo_correction *= np.exp(2.0j * np.pi * fine_offset * np.arange(len(data_frame)))
        print("fine offset: ", fine_offset * fs, "Hz")

        data_frame = data_frame * cfo_correction

        # rough phase correction
        phase = np.average(data_frame)
        phase = phase / (np.abs(phase) + 1e-9)
        data_frame = data_frame * np.conj(phase)


        self.frame_angle_ax.plot(np.arange(len(data_frame)), np.angle(cfo_correction)/ (np.pi), label="θ estimate")
        self.frame_angle_ax.plot(np.arange(len(data_frame)), np.angle(data_frame), label="s_θ corrected")

        # demodulate frame
        #frame_demod = self.ofdm.demodulate(frame)
        #frame_demod = frame_demod/np.max(np.abs(frame_demod))
        ##self.constellation_ax.scatter(frame_demod.real, frame_demod.imag)

        self.frame_iq_ax.plot(np.arange(len(data_frame)) + self.ofdm.CP + self.ofdm.K, data_frame.real, label="real(s)")
        self.frame_iq_ax.plot(np.arange(len(data_frame)) + self.ofdm.CP + self.ofdm.K, data_frame.imag, label="imag(s)")

        self.draw_plots()

    ################# ACTIONS ###################

    def rx(self):
        self.sdrplusman.rx_buffer_size = 100000
        self.sdrplusman.rebuild_rx_buffer()

        # clear buffer
        for i in range(10):
            self.sdrplusman.sdr.rx()

        t = np.arange(self.sdrplusman.rx_buffer_size)/fs
        samples = self.sdrplusman.sdr.rx()
        samples = samples * np.exp(-2.0j*np.pi*3000*t)

        # normalize
        samples /= (np.percentile(np.abs(samples), 99) + 1e-9)

        return samples

    def tx(self):
        self.sdrman.rebuild_tx_buffer()
        
        samples = self.preamble()
        samples = np.hstack([samples, self.random_symbols_DC_4psk()])

        txnullpad = 10000
        samples = np.pad(samples, txnullpad)

        t = np.arange(len(samples))/fs
        metric, P, R = self.calc_metric(samples)

        #samples += (np.random.rand(len(samples)) + 1j*np.random.rand(len(samples))-.5-.5j) * 0.5

        ###### TX PLOTTING
        self.tx_frame_iq_ax.plot(np.arange(len(samples)), (samples.real), label="real(s)")
        self.tx_frame_iq_ax.plot(np.arange(len(samples)), (samples.imag), label="imag(s)")
        self.tx_frame_iq_ax.plot(np.arange(len(P)), (np.angle(P)), label="∠P")
        self.tx_frame_iq_ax.plot(np.arange(len(metric)), (np.angle(metric)), label="|metric|")

        self.tx_frame_iq_ax.axvline(x=txnullpad, color='black') # CP start
        self.tx_frame_iq_ax.axvline(x=txnullpad+self.ofdm.CP, color='black') # preamble start
        self.tx_frame_iq_ax.axvline(x=txnullpad+self.ofdm.CP+self.ofdm.K, color='black') # cox preamble end
        self.tx_frame_iq_ax.axvline(x=txnullpad+2*(self.ofdm.CP+self.ofdm.K), color='black') # cfo preamble end

        # plot fft
        fft_f, psd_dB = self.fft_graph(samples, fs)
        self.tx_fft_ax.plot(fft_f, psd_dB)

        samples *= np.exp(2.0j*np.pi*3000*t) # to allow for DC QAM signals
        samples *= 2**13
        t = np.arange(len(samples))/fs
        self.sdrman.cyclic_tx(samples)

    def stop_tx(self):
        self.sdrman.stop_cyclic_tx()

    ################## CALCULATIONS #######################

    def calc_metric(self, samples):
        L = self.ofdm.K//2
        P = samples * (np.pad(samples, (0,L))[L:]).conj() # x[n] * x[n-L].conj()
        P = np.convolve(P, np.ones(L), mode="valid") # sumnation
        R = np.convolve(np.square(np.abs(samples)), np.ones(L), mode="valid") # sig strength

        R = R[L:]  # shift left
        P = P[:-L] # cut to length

        metric = (np.abs(np.square(P))) / (np.square(R) + 1e-9)

        return metric, P, R

    def sync_from_metric(self, metric):
        metric = np.convolve(metric, np.ones(self.ofdm.CP)/self.ofdm.CP)
        diff = np.diff(metric)

        metric = ((diff[:-1] * diff[1:]) <= 0) * (metric[1:-1] > 0.75) * 1 # zero crossings in metric

        ignore_window = np.ones(self.ofdm.CP + self.ofdm.K + 2000)
        ignore_window[-1] = 0

        ignore = np.convolve(metric, ignore_window, mode="valid")
        ignore = np.pad(ignore, (self.ofdm.CP + self.ofdm.K + 2000, 0), mode="constant", constant_values=1)[:-1]
        metric = metric * (ignore == 0)

        return metric

    def frame_start_inds_and_arg_p(self, samples):
        metric, P, R = self.calc_metric(samples)
        sync = self.sync_from_metric(metric)

        start_inds = np.flatnonzero(sync)

        return start_inds, np.angle(P)
 

    ##################### STRUCTURE #####################

    def preamble(self):
        # cox preamble for sync
        cox_freqs = self.ofdm.random_carriers_4psk()
        cox_freqs[1::2] = 0
        cox_preamble = self.ofdm.modulate(cox_freqs)
        self.saved_cox_preamble = cox_preamble

        # fixed pilot for carrier frequency offset estimation
        cfo_freqs = np.zeros(self.ofdm.Kon)
        cfo_freqs[0] = np.sqrt(self.ofdm.K) # lowest positive carrier
        cfo_preamble = self.ofdm.modulate(cfo_freqs)

        return np.hstack([cox_preamble, cfo_preamble])

    # dummy data
    def random_symbols_DC_4psk(self):
        samples = []

        for i in range(10):
            data = np.repeat([1+1j, 1-1j, -1+1j, -1-1j][i%4], self.ofdm.K + self.ofdm.CP)
            samples = np.hstack([samples, data])

        samples = np.repeat(1+1j, (self.ofdm.K + self.ofdm.CP) * 10)
        return samples

    def extract_frame_parts(self, samples, frame_start, data_symbols=10):
        i = frame_start
        K = self.ofdm.K
        CP = self.ofdm.CP

        full_frame   = samples[i - CP     : i + K + (K + CP) * (data_symbols+1)] # plotting only
        cox_preamble = samples[i          : i + K]
        cfo_preamble = samples[i + K + CP : i + 2*K + CP]

        data_frames = []
        for ii in range(data_symbols):
            data_frames.append(samples[i + (2+ii)*(K + CP) : i + (2+ii)*(K + CP) + K])

        full_data = samples[i + (2)*(K + CP) : i + (1+data_symbols)*(K + CP) + K]

        return full_frame, cox_preamble, cfo_preamble, data_frames, full_data