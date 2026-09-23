import numpy as np
import adi
import matplotlib.pyplot as plt
from gui import *

from apps.cwtest import CWTest
from apps.liverx import LiveRX
from apps.sync1  import Sync1
from apps.framesync  import FrameSync
from apps.schmidl_cox  import SchmidlCox

sample_rate = 1e6 # Hz
center_freq = 915e6 # Hz
num_samps = 10000 # number of samples per call to rx()

# Config Tx
class SDRManager:
    def __init__(self, uri):
        #iio_info -s
        self.sdr = adi.Pluto(uri)
        #192.168.3.1
        self.sdr.sample_rate = int(sample_rate)

        self.tx_rf_bandwidth = int(sample_rate)
        self.tx_lo = int(center_freq)
        self.tx_hardwaregain_chan0 = -20 # -90 to 0 dB

        self.tx_cyclic_buffer = False
        self.tx_cyclic_buffer_samples = []

        self.rx_lo = int(center_freq)
        self.rx_rf_bandwidth = int(sample_rate)
        self.rx_buffer_size = num_samps
        self.gain_control_mode_chan0 = 'manual'
        self.rx_hardwaregain_chan0 = 20 # 0 - 70

        self.rebuild_rx_buffer()
        self.rebuild_tx_buffer()

    def rebuild_tx_buffer(self):
        self.sdr.tx_destroy_buffer()

        self.sdr.tx_rf_bandwidth = self.tx_rf_bandwidth
        self.sdr.tx_lo = self.tx_lo
        self.sdr.tx_hardwaregain_chan0 = self.tx_hardwaregain_chan0

        self.sdr.tx_cyclic_buffer = self.tx_cyclic_buffer
        if (self.tx_cyclic_buffer):
            self.sdr.tx(self.tx_cyclic_buffer_samples)

    def rebuild_rx_buffer(self):
        self.sdr.rx_destroy_buffer()

        self.sdr.rx_lo = self.rx_lo
        self.sdr.rx_rf_bandwidth = self.rx_rf_bandwidth
        self.sdr.rx_buffer_size = self.rx_buffer_size
        self.sdr.gain_control_mode_chan0 = self.gain_control_mode_chan0
        self.sdr.rx_hardwaregain_chan0 = self.rx_hardwaregain_chan0

    def cyclic_tx(self, samples):
        self.tx_cyclic_buffer = True
        self.tx_cyclic_buffer_samples = samples

        self.rebuild_tx_buffer()

    def stop_cyclic_tx(self):
        self.tx_cyclic_buffer = False
        self.tx_cyclic_buffer_samples = []

        self.rebuild_tx_buffer()


a = 0
def rx_plot():
    global a
    samples = sdrman.sdr.rx()

    # Create matplotlib figure
    fig, ax = plt.subplots(figsize=(3, 3))

    ax.plot(np.arange(len(samples)), samples.real)
    ax.set_title("Plot! " + str(a))
    a += 1
    ax.grid(True)
    
    return fig

# iio_info -u "ip:169.254.12.16" -s
sdrman      = SDRManager("ip:192.168.2.1") # reg
sdrplusman  = SDRManager("ip:10.3.33.236") # plus
#sdrman = SDRManager("ip:169.254.12.16") # plus

################# GUI CONTROLS ###############
gui = GUI()

def set_agc_mode(mode):
    if   mode == "Manual":      sdrman.gain_control_mode_chan0 = "manual"
    elif mode == "Fast Attack": sdrman.gain_control_mode_chan0 = "fast_attack"
    elif mode == "Slow Attack": sdrman.gain_control_mode_chan0 = "slow_attack"
    sdrman.rebuild_rx_buffer()

def set_tx_enable(enable):
    print(enable)
    if (enable):
        pass
        #sdrman.tx_cyclic_buffer = True
        #sdrman.rebuild_tx_buffer()
    else:
        sdrman.tx_destroy_buffer()

def set_tx_gain(val):
    sdrman.tx_hardwaregain_chan0 = int(val)
    sdrman.rebuild_tx_buffer()

def set_manual_rx_gain(val):
    sdrman.rx_hardwaregain_chan0 = int(val)
    sdrman.rebuild_rx_buffer()

####################
# rx general
#gui.rx_controls.live_rx_callback         = lambda checked : print("live rx: " + str(checked))
gui.rx_controls.set_manaul_gain_callback = set_manual_rx_gain
gui.rx_controls.set_auto_gain_callback   = set_agc_mode
gui.rx_controls.probe_usb_callback       = lambda : print("probe usb")

# tx general
gui.tx_controls.tx_enable_callback     = set_tx_enable
gui.tx_controls.set_gain_callback      = set_tx_gain

########## GUI APPS ##########
# cw test (in rx controls)
cw_test = CWTest(sdrman)
def test_cw(checked):
    if checked: cw_test.tx()
    else:       cw_test.stop_tx()

gui.tx_controls.test_cw_check_callback = test_cw
gui.tx_controls.set_cw_offset_callback = cw_test.set_freq

############### ADD APPS 3
# live rx
live_rx = LiveRX(sdrplusman, gui)
gui.rx_controls.live_rx_callback   = lambda checked : (live_rx.start() if checked else live_rx.stop())
gui.rx_controls.single_rx_callback = lambda : live_rx.single_rx()

# sync 1
sync1 = Sync1(sdrman, gui)
gui.comms_control.sync1_callback = sync1.start
#sync1.start()

# frame sync
frame_sync = FrameSync(sdrman, sdrplusman, gui)
gui.comms_control.frame_sync_callback = frame_sync.start

# schmidl cox
cox = SchmidlCox(sdrman, sdrplusman, gui)
gui.comms_control.cox_callback = cox.start

cox.start()
gui.root.mainloop()