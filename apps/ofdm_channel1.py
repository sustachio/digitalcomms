
import numpy as np
import adi
import matplotlib.pyplot as plt
from scipy import signal, fft
import time
from apps.app_parent import *

fs = 1e6

norm99 = lambda v : v / (np.percentile(np.abs(v), 99) + 1e-9)

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
        freqs = freqs[offset : offset + self.Kon]
        #freqs = np.fft.fftshift(freqs)

        return freqs

    def random_carriers_4psk(self):
        qam = np.array([1+1j, 1-1j, -1+1j, -1-1j]) * np.sqrt(2)
        return np.random.choice(qam, size=self.Kon, replace=True)





class OFDMChannelEst1(App):
    def __init__(self, sdrman, sdrplusman, gui):
        super().__init__(sdrman, sdrplusman, gui)
        self.name = "OFDM Block Channel Estimation"
        self.description = "OFDM modulation with block channel estimation"
        self.gui_elements = [GUIButton("Start", self.start)]

        self.iq_ax            = self.new_plot("rx", "Raw I/Q", ybounds=(-2, 2))
        self.frame_iq_ax      = self.new_plot("rx", "Frame I/Q", ybounds=(-np.pi, np.pi))
        self.constellation_ax = self.new_plot("rx", "I/Q Constellation")
        self.estimation_ax   = self.new_plot("rx", "Channel Estimation", ybounds=(-np.pi, np.pi))

        self.tx_frame_iq_ax   = self.new_plot("tx", "Frame I/Q", ybounds=(-3, 3))
        self.tx_fft_ax        = self.new_plot("tx", "FFT", ybounds=(-30, 0))

        self.ofdm = OFDM(1024, 600, 128)
        #self.ofdm = OFDM(100, 40, 20)

        self.Nsymbols = 2
        self.pilots = self.ofdm.random_carriers_4psk()

        self.saved_cox_preamble = []

    def start(self):
        self.reset_plots()

        self.tx()
        samples = self.rx()
        self.stop_tx()

        # calculate frame start
        frame_start_inds, P = self.frame_start_inds_and_p(samples)
        frame_start = frame_start_inds[1]

        # extract parts
        full_frame, cox_preamble, cfo_preamble, data_frames, full_data = self.extract_frame_parts(samples, frame_start, self.Nsymbols)
        data_frame = np.hstack(data_frames)

        self.iq_ax.plot(np.arange(len(samples)), (samples.real), label="real(s)")
        self.iq_ax.axvline(x=frame_start, color='red', label="frame start")

        self.frame_iq_ax.plot(np.arange(len(full_frame)), np.abs(full_frame), label="|s|")

        # cfo correction
        n = 5
        data_frame, coarse_offset, peak_bin, cfo_correction = self.correct_cfo(data_frame, P[frame_start], cfo_preamble, n)

        # measure pilots
        measured_pilots = self.ofdm.demodulate(data_frame[self.ofdm.CP : self.ofdm.CP + self.ofdm.K])
        #measured_pilots = norm99(measured_pilots)

        data = self.ofdm.demodulate(data_frame[-self.ofdm.K:])
        estimation = self.pilots / measured_pilots
        self.estimation_ax.plot(np.arange(len(estimation)), np.angle(estimation), label="∠est")
        self.estimation_ax.plot(np.arange(len(estimation)), norm99(np.abs(estimation)), label="|est|")

        # correct next block
        for i in range(self.ofdm.Kon):
            data[i] *= (estimation[i])
        #data = norm99(data)
        self.constellation_ax.scatter(estimation.real, estimation.imag, label="est")
        self.constellation_ax.scatter(data.real, data.imag, label="data")


        graph_sample = samples[frame_start - self.ofdm.K: frame_start + (2+self.Nsymbols)*(self.ofdm.K + self.ofdm.CP)]
        frame_graph_x = np.arange(-self.ofdm.K, (2+self.Nsymbols)*(self.ofdm.K + self.ofdm.CP))
        self.frame_iq_ax.plot(frame_graph_x, graph_sample.real, label="real(s)")
        self.frame_iq_ax.plot(np.arange(self.Nsymbols * (self.ofdm.CP + self.ofdm.K)) + self.ofdm.K*2 + self.ofdm.CP, data_frame.real, label="real(corrected s)")
        #self.frame_iq_ax.plot(frame_graph_x, graph_sample.imag, label="imag(s)")
        #self.frame_iq_ax.plot(np.arange(len(data_frame)) + self.ofdm.CP + 2*self.ofdm.K, np.angle(data_frame), label="θ(s)")

        self.frame_iq_ax.axvline(x=0, color='black') # prefix K start
        for i in range(self.Nsymbols+2):
            self.frame_iq_ax.axvline(x=i*(self.ofdm.K+self.ofdm.CP)+self.ofdm.K, color='black') # CP start

        #self.frame_iq_ax.plot(np.arange(len(data_frame)) + self.ofdm.CP + 2*self.ofdm.K, data_frame.real, label="real(s)")

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

        # normalize
        samples = norm99(samples)

        return samples

    def tx(self):
        self.sdrman.rebuild_tx_buffer()
        
        samples = self.preamble()
        samples = np.hstack([samples, self.ofdm.modulate(self.pilots), self.ofdm.modulate(self.ofdm.random_carriers_4psk())])

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

    def frame_start_inds_and_p(self, samples):
        metric, P, R = self.calc_metric(samples)
        sync = self.sync_from_metric(metric)

        start_inds = np.flatnonzero(sync)

        return start_inds, P
 
    # coarse/fine CFO correction
    def correct_cfo(self, data_frame, P_frame_start, cfo_preamble, n=5): # n points to each side
        fft_mag = np.abs(np.fft.fft(cfo_preamble))
        peak_bin = np.argmax(fft_mag)

        domain = np.arange(peak_bin-n, peak_bin+n+1)
        y = fft_mag[domain]
        y /= np.max(y)

        p = np.polyfit(domain, y, 2)
        peak_bin = -p[1] / (2*p[0]) # vertex
    
        coarse_offset = ((self.ofdm.K - self.ofdm.Kon) / 2 - peak_bin)

        cfo_correction = np.exp(2.0j * np.pi * coarse_offset * np.arange(len(data_frame)) / self.ofdm.K)
        print("coarse offset: ", coarse_offset * fs / self.ofdm.K)

        # fine cfo
        fine_offset = np.angle(P_frame_start * np.exp(-1.0j * np.pi * coarse_offset)) 
        cfo_correction *= np.exp(2.0j * fine_offset * np.arange(len(data_frame)) / self.ofdm.K)
        print("fine offset: ", fine_offset * fs / self.ofdm.K, "Hz")

        data_frame *= cfo_correction

        return data_frame, coarse_offset, peak_bin, cfo_correction


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
            #data_frames.append(samples[i + (2+ii)*(K + CP) : i + (2+ii)*(K + CP) + K]) # remove CP
            data_frames.append(samples[i + (2+ii)*(K + CP) - CP : i + (2+ii)*(K + CP) + K]) # keep CP

        full_data = samples[i + (2)*(K + CP) : i + (1+data_symbols)*(K + CP) + K]

        return full_frame, cox_preamble, cfo_preamble, data_frames, full_data