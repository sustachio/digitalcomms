import numpy as np
import adi
import matplotlib.pyplot as plt

sample_rate = 1e6

class LiveRX():
    def __init__(self, sdrman, gui):
        self.sdrman = sdrman
        self.gui = gui

        self.a = 0
        self.fig, self.ax = plt.subplots(figsize=(3, 3))

        self.ax.grid(True)
        self.ax.set_ylim(-100,100)
        self.axcanvas = gui.rx_graphs.add_plot(self.fig)

        self.running = False

    def start(self):
        self.running = True
        self.gui.root.after(10, self.update_live_rx)

    def single_rx(self):
        # clear buffer
        for i in range(10):
            self.sdrman.rx()
        
        self.running = False
        self.gui.root.after(10, self.update_live_rx)

    def stop(self):
        self.running = False

    def update_live_rx(self):
        samples = self.sdrman.sdr.rx()

        self.ax.cla()
        self.ax.plot(np.arange(len(samples)), samples.real)
        self.ax.set_title("Plot! " + str(self.a))
        self.ax.set_ylim(-100,100)
        self.axcanvas.draw()
        self.a+=1

        if self.running:
            self.gui.root.after(10, self.update_live_rx)
