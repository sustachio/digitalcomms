import matplotlib.pyplot as plt

class App:
    def __init__(self, sdrman, gui):
        self.sdrman = sdrman
        self.gui = gui

        self.axs = []
        self.figs = []
        self.ax_canvases = []
        self.locations = [] # rx or tx

    def new_plot(self, location, title, ybounds=(0,0), xbounds=(0,0)):
        fig, ax = plt.subplots(figsize=(3, 3))
        ax.grid(True)
        if ybounds != (0,0):
          ax.set_ylim(ybounds[0], ybounds[1])
        if xbounds != (0,0):
          ax.set_xlim(xbounds[0], xbounds[1])
        ax.set_title(title)

        self.figs.append(fig)
        self.axs.append(ax)
        self.locations.append(location)

        return ax

    def reset_plots(self, clear_all=True):
        if clear_all:
            self.gui.clear_graphs()

        # add to gui
        self.ax_canvases = []
        for (location, fig) in zip(self.locations, self.figs):
            if location == "rx":
                self.ax_canvases.append(self.gui.rx_graphs.add_plot(fig))
            elif location == "tx":
                self.ax_canvases.append(self.gui.tx_graphs.add_plot(fig))
            else:
                raise ValueError("unknown plot location " + location)

        # clear lines
        for ax in self.axs:
            ax.set_prop_cycle(None) # reset color cycle
            for line in list(ax.lines):
                line.remove()
            for collection in list(ax.collections):
                collection.remove()

    def draw_plots(self):
        for canvas in self.ax_canvases:
            canvas.draw_idle()

