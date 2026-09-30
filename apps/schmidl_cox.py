
import numpy as np
import adi
import matplotlib.pyplot as plt
from scipy import signal, fft
import time
from apps.app_parent import App

fs = 1e6

L=200
pad_len = 1000


class SchmidlCox(App):
    def __init__(self, sdrman, sdrplusman, gui):
        super().__init__(sdrman, sdrplusman, gui)

        self.iq_ax            = self.new_plot("rx", "Raw I/Q", ybounds=(-100, 100))
        self.constellation_ax = self.new_plot("rx", "I/Q Constellation", ybounds=(-100, 100), xbounds=(-100,100))
        self.frame_iq_ax      = self.new_plot("rx", "Frame I/Q", ybounds=(-100, 100))
        self.tx_frame_iq_ax   = self.new_plot("tx", "Frame I/Q", ybounds=(-3, 3))
        self.tx_fft_ax        = self.new_plot("tx", "FFT", ybounds=(-30, 0))


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
        samples += (np.random.rand(len(samples)) + 1j*np.random.rand(len(samples)))*100
        #samples_interpolated = signal.resample_poly(samples, 16, 1)

        # preamble detection
        correlation = samples * np.conj(np.pad(samples, (20,0)))[:len(samples)]
        correlation = np.convolve(correlation, np.ones(40), mode="valid") # moving average


        #correlation = signal.correlate(samples, self.generate_samples(self.preamble_symbols), mode="valid")
        #correlation = abs(correlation)
        #correlation = correlation / (max(correlation)) * 60

        #frame_start = np.argmax(correlation)
        #frame = samples[frame_start:frame_start+(Nsymbols+preamble_length)*cycles_per_symbol]

        self.stop_tx()

        #self.iq_ax.plot(np.arange(len(samples)), samples.real)
        #self.iq_ax.plot(np.arange(len(samples)), samples.imag)
        #self.iq_ax.plot(np.arange(len(correlation)), np.abs(correlation))

        self.iq_ax.plot(np.arange(len(samples)), np.abs(samples))
        # each row is one L_test length
        metric = np.zeros((L*2-10, len(samples))).astype(complex)
        for L_test in range(L-5, L+5):
            for d in range(len(samples) - L_test*2):
                for m in range(L_test-1):
                    metric[L_test+5][d] += samples[d+m].conj() * samples[d+m+L_test]

            print(L_test)

        delays = np.sum(metric, axis=1)
        best_delay = np.argmax(delays)

        self.iq_ax.plot(np.arange(len(metric[best_delay])), np.abs(metric[best_delay])/np.max(np.abs(metric[best_delay]))*1000)
        self.iq_ax.plot(np.arange(len(delays)), np.abs(delays)/np.max(np.abs(delays))*1000)

        #self.frame_iq_ax.plot(np.arange(len(frame)), frame.real)
        #self.frame_iq_ax.plot(np.arange(len(frame)), frame.imag)

        self.constellation_ax.scatter(samples.real, samples.imag)

        self.draw_plots()

    def generate_samples(self, symbols):
        symbols = np.repeat(symbols, cycles_per_symbol)
        samples = np.exp(1j*symbols * np.pi/2 + np.pi/4)

        return samples

    def tx(self):
        self.sdrman.rebuild_tx_buffer()

        cox_freqs = np.random.rand(2*L).astype(complex)
        #cox_freqs = np.zeros(41)
        cox_freqs[1::2] = 0
        #cox_freqs[20] = 0 # remove DC
        #cox_freqs[1::2] = 1
        #cox_freqs[1:10:2] = 1
        #cox_freqs[1] = 1
        #cox_freqs[3] = 1

        samples = fft.ifft(cox_freqs, norm="forward")
        samples = np.pad(samples, pad_len)
        #samples += np.random.rand(len(samples)) + 1j*np.random.rand(len(samples))

        metric = np.zeros(L*2 + pad_len*2).astype(complex)
        for d in range(len(samples) - L*2):
            met = 0
            for m in range(L):
                met += samples[d+m].conj() * samples[d+m+L]
            metric[d] = met
        #metric = samples * (np.pad(samples, (L, 0))[:-L]).conj()
        #metric = np.pad(samples, (20, 0))[:-20]
        #metric = np.convolve(metric, np.ones(40), mode="valid")

        self.tx_frame_iq_ax.plot(np.arange(len(samples)), np.abs(samples))
        #self.tx_frame_iq_ax.plot(np.arange(len(samples)), samples.imag)
        self.tx_frame_iq_ax.plot(np.arange(len(metric))-20, np.abs(metric)/np.max(np.abs(metric)))

        spacepad_len = 3000
        samples = np.pad(samples, spacepad_len)

        t = np.arange(len(samples))/fs - spacepad_len/fs
        samples *= 0.5*np.exp(2.0j*np.pi*5000*t)
        samples *= 2**14

        # plot fft
        psd = np.abs(np.fft.fftshift(np.fft.fft(samples/(2**14))))**2
        psd_dB = 10*np.log10(psd+1e-6)
        fft_f = np.linspace(fs/-2, fs/2, len(psd_dB))
        psd_dB -= np.max(psd_dB)

        self.tx_fft_ax.plot(fft_f, psd_dB)
        #self.tx_fft_ax.plot(np.arange(len(samples)), samples)

        self.sdrman.cyclic_tx(samples)

    def stop_tx(self):
        self.sdrman.stop_cyclic_tx()

