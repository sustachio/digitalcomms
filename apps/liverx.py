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

        self.running = False

        self.line = None

    def start(self):
        self.axcanvas = self.gui.rx_graphs.add_plot(self.fig)

        self.running = True
        self.gui.root.after(10, self.update_live_rx)

    def single_rx(self):
        self.axcanvas = self.gui.rx_graphs.add_plot(self.fig)

        # clear buffer
        for i in range(10):
            self.sdrman.sdr.rx()
        
        self.running = False
        self.gui.root.after(10, self.update_live_rx)

    def stop(self):
        self.running = False

    def update_live_rx(self):
        samples = self.sdrman.sdr.rx()

        if self.line:
            self.line.remove()
        self.line, = self.ax.plot(np.arange(len(samples)), samples.real, color="blue")
        self.ax.set_title("Plot! " + str(self.a))
        self.axcanvas.draw()
        self.a+=1

        if self.running:
            self.gui.root.after(10, self.update_live_rx)
