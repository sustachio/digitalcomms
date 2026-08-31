import numpy as np
import adi
import matplotlib.pyplot as plt
from gui import *

sample_rate = 1e6 # Hz
center_freq = 915e6 # Hz
num_samps = 10000 # number of samples per call to rx()

sdr = adi.Pluto("ip:192.168.2.1")
sdr.sample_rate = int(sample_rate)

# Config Tx
sdr.tx_rf_bandwidth = int(sample_rate) # filter cutoff, same as sample rate
sdr.tx_lo = int(center_freq)
sdr.tx_hardwaregain_chan0 = -50 # -90 to 0 dB

# Config Rx
sdr.rx_lo = int(center_freq)
sdr.rx_rf_bandwidth = int(sample_rate)
sdr.rx_buffer_size = num_samps
sdr.gain_control_mode_chan0 = 'manual'
sdr.rx_hardwaregain_chan0 = 50 # 0 - 70

"""
# Create transmit waveform (QPSK, 16 samples per symbol)
num_symbols = 1000
x_int = np.random.randint(0, 4, num_symbols) # 0 to 3
x_degrees = x_int*360/4.0 + 45 # 45, 135, 225, 315 degrees
x_radians = x_degrees*np.pi/180.0 # sin() and cos() takes in radians
x_symbols = np.cos(x_radians) + 1j*np.sin(x_radians) # this produces our QPSK complex symbols
samples = np.repeat(x_symbols, 16) # 16 samples per symbol (rectangular pulses)
samples *= 2**14 # The PlutoSDR expects samples to be between -2^14 and +2^14, not -1 and +1 like some SDRs

# Start the transmitter
sdr.tx_cyclic_buffer = True # Enable cyclic buffers
sdr.tx(samples) # start transmitting

# Clear buffer just to be safe
#for i in range (0, 10):
    #raw_data = sdr.rx()

# Receive samples
rx_samples = sdr.rx()
print(rx_samples)

# Stop transmitting
sdr.tx_destroy_buffer()

# Calculate power spectral density (frequency domain version of signal)
psd = np.abs(np.fft.fftshift(np.fft.fft(rx_samples)))**2
psd_dB = 10*np.log10(psd)
f = np.linspace(sample_rate/-2, sample_rate/2, len(psd))

# Plot time domain
plt.figure(0)
plt.plot(np.real(rx_samples[::100]))
plt.plot(np.imag(rx_samples[::100]))
plt.xlabel("Time")

# Plot freq domain
plt.figure(1)
plt.plot(f/1e6, psd_dB)
plt.xlabel("Frequency [MHz]")
plt.ylabel("PSD")
plt.show()
"""

def test_cw_callback(checked):
    if checked:
        print("testing CW")
        N = 10000
        t = np.arange(N)/sample_rate
        samples = 0.5*np.exp(2.0j*np.pi*100e3*t)
        sameples *= 2**14

        sdr.tx_cyclic_buffer = True # Enable cyclic buffers
        sdr.tx(samples) # start transmitting
    else:
        print("stopping CW")
        sdr.tx_destroy_buffer()

a = 0
def rx_plot():
    global a
    samples = sdr.rx()

    # Create matplotlib figure
    fig, ax = plt.subplots(figsize=(3, 3))

    ax.plot(np.arange(len(samples)), samples.real)
    ax.set_title("Plot! " + str(a))
    a += 1
    ax.grid(True)
    
    return fig

gui = GUI()

gui.rx_controls.live_rx_callback         = lambda checked : print("live rx: " + str(checked))
gui.rx_controls.single_rx_callback       = lambda : gui.rx_graphs.add_plot(rx_plot())
gui.rx_controls.set_manaul_gain_callback = lambda val_db : print("set manual rx gain: " + val_db)
gui.rx_controls.set_auto_gain_callback   = lambda agc_setting : print("agc setting: " + agc_setting)
gui.rx_controls.probe_usb_callback       = lambda : print("probe usb")

gui.tx_controls.tx_enable_callback     = lambda checked : print("tx enable: " + str(checked))
gui.tx_controls.set_gain_callback      = lambda val : print("set tx gain: " + val)
gui.tx_controls.test_cw_check_callback = test_cw_callback
gui.tx_controls.set_cw_offset_callback = lambda freq : print("set cw offset: " + str(freq))

root.mainloop()