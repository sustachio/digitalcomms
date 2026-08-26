from tkinter import *
from tkinter import ttk

from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure

import numpy as np

class GUI:
    def __init__(self, pluto):
        self.root = Tk()
        self.root.title("Seth's Digital Comms")
        #self.root.columnconfigure(0, weight=1)
        #self.root.rowconfigure(0, weight=1)

        #self.main_frame = ttk.Frame(self.root, padding=3)
        #self.main_frame.grid(row=0, column=0, sticky=(N,S,E,W))

        fig = Figure(figsize=(5, 4), dpi=100)
        t = np.arange(0, 3, .01)
        fig.add_subplot(111).plot(t, 2 * np.sin(2 * np.pi * t))

        canvas = FigureCanvasTkAgg(fig, master=self.root)  # A tk.DrawingArea.
        canvas.draw()
        canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)

        toolbar = NavigationToolbar2Tk(canvas, self.root)
        toolbar.update()
        canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)


        #self.ui_basic_rx()

    def mainloop(self):
        return self.root.mainloop()

    def rx_button(self, *args):
        self.data_text.set("blub")
        print("rx")

    def ui_basic_rx(self):
        # | data: | `data_text` |
        result_frame = ttk.Frame(self.main_frame).grid(row=0, column=0)
        self.data_text = StringVar()
        ttk.Label(result_frame, text="Data: ").grid(row=0, column=0)
        ttk.Label(result_frame, textvariable=self.data_text).grid(row=0, column=1)

        # [ RX ]
        ttk.Button(self.main_frame, text="RX", command=self.rx_button).grid(row=1, column=0)

        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=3)
        self.main_frame.rowconfigure(1, weight=1)
        for child in self.main_frame.winfo_children(): 
            child.grid_configure(padx=5, pady=5)

gui = GUI(0)
gui.mainloop()