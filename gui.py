from tkinter import *
from tkinter import ttk
from tkinter import font

from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure

import numpy as np

from PIL import Image, ImageTk

root = Tk()

default_font = font.nametofont("TkDefaultFont")
default_font.configure(size=12)
bu_font = default_font.copy() # bold underline
bu_font.configure(underline=True, weight="bold")
u_font = default_font.copy() # underline
u_font.configure(underline=True)
b_font = default_font.copy() # bold
b_font.configure(weight="bold")


class GUI:
    def __init__(self):
      self.window_init()

      main_frame = ttk.Frame(root, padding=3)
      main_frame.grid(row=0, column=0, sticky="nsew")
      main_frame.rowconfigure([0,1], weight=1, uniform="rows")

      # red / blue titles
      ttk.Label(main_frame, text="TX", foreground="white", background="red", anchor="center") \
          .grid(row=1, column=0, sticky="nsew")
      ttk.Label(main_frame, text="RX", foreground="white", background="blue", anchor="center") \
          .grid(row=0, column=0, sticky="nsew")
      main_frame.columnconfigure(0, weight=0, minsize=50)

      # graphs
      RXGraphs(main_frame).grid(row=0, column=1, sticky="nsew")
      TXGraphs(main_frame).grid(row=1, column=1, sticky="nsew")
      main_frame.columnconfigure(1, weight=2)

      # controls
      RXControl(main_frame).grid(row=0, column=2, sticky="nsew")
      TXControl(main_frame).grid(row=1, column=2, sticky="nsew")
      main_frame.columnconfigure(2, weight=1)

      ttk.Separator(main_frame, orient=VERTICAL).grid(row=0, column=3, sticky="nsew", rowspan=2)
      main_frame.columnconfigure(3, weight=0)

      CommsControl(main_frame).grid(row=0, column=4, sticky="nsew", rowspan=2)
      main_frame.columnconfigure(4, weight=1)
      
      for child in main_frame.winfo_children():
        child.grid_configure(padx=4, pady=4)

    ################ UTILS ##############
    def window_init(self):
      root.geometry("1200x800")
      root.title("super cool digital communications thing +_+")
      root.columnconfigure(0, weight=1)
      root.rowconfigure(0, weight=1)

    ############### CALLBACKS ##############
    def rx_button(self, *args):
      self.data_text.set("blub")
      print("rx")


class ResizingFrame(ttk.Frame):
  def __init__(self, parent):
    super().__init__(parent)

    self.rowconfigure(0, weight=1)
    self.columnconfigure(0, weight=1)


# large w/ scrollbar section to hold the graphs
class HScrollable(ResizingFrame):
  def __init__(self, parent):
    super().__init__(parent)
    
    self.canvas = Canvas(self)
    self.scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)

    self.canvas.configure(xscrollcommand=self.scrollbar.set)

    self.canvas   .pack(side="top",    fill="both", expand=True)
    self.scrollbar.pack(side="bottom", fill="x")

    # where graphs go
    self.main_frame = Frame(self.canvas)
    self.canvas_window = self.canvas.create_window((0,0), window=self.main_frame, anchor="nw")

    # update canvas when plot_frame changes size
    self.main_frame.bind("<Configure>", self._update_scrollregion)

  def _update_scrollregion(self, event=None):
    self.canvas.configure(scrollregion=self.canvas.bbox("all"))

class RXGraphs(HScrollable):
  def __init__(self, parent):
    super().__init__(parent)

    self.config(relief="ridge", padding=(10,10,10,10))

    ttk.Label(self.main_frame, text="I/Q constelations").grid(sticky="w")
    ttk.Label(self.main_frame, text="FFT").grid(sticky="w")
    ttk.Label(self.main_frame, text="Sync").grid(sticky="w")
    ttk.Label(self.main_frame, text="USB").grid(sticky="w")

class TXGraphs(HScrollable):
  def __init__(self, parent):
    super().__init__(parent)

    self.config(relief="ridge", padding=(10,10,10,10))

    ttk.Label(self.main_frame, text="I/Q constelations").grid(sticky="w")
    ttk.Label(self.main_frame, text="FFT").grid(sticky="w")
    ttk.Label(self.main_frame, text="hello!!!!", font=bu_font).grid(sticky="w")
    ttk.Label(self.main_frame, text="hiii!!!!").grid(sticky="w")

class RXControl(ResizingFrame):
  def __init__(self, parent):
    super().__init__(parent)

    self.config(relief="ridge", padding=(10,10,10,10))

    ttk.Label(self, text="Reciever control (PlutoSDR)", font=bu_font) \
       .pack(anchor="w", pady=(0,10))

    # live rx
    b_live_rx = BooleanVar(value=False)
    ttk.Checkbutton(self, text="Live Receive", variable=b_live_rx, command=lambda : print(b_live_rx.get())).pack(anchor="w")

    # single rx
    ttk.Button(self, text="Single Receive", command=lambda : print("single RX")).pack(anchor="w")

    ttk.Separator(self, orient=HORIZONTAL).pack(fill="x", pady=3)

    # rx gain
    rx_gain_agc = BooleanVar(value=False)
    ttk.Checkbutton(self, text="Automatic Gain Control", variable=rx_gain_agc, command=lambda : print(b_live_rx.get())).pack(anchor="w")

    rx_gain_frame = ttk.Frame(self)
    rx_gain_frame.pack(anchor="w")
    ttk.Label(rx_gain_frame, text="RX Gain (dB)").pack(side="left")
    rx_gain_slider = Scale(rx_gain_frame, from_=0, to=70, orient=HORIZONTAL)
    rx_gain_slider.pack(side="left")

    ttk.Separator(self, orient=HORIZONTAL).pack(fill="x", pady=3)

    # probe usb
    ttk.Button(self, text="Probe USB", command=lambda : print("usb probed")).pack(anchor="w")
    ttk.Label(self, text="Max rate: ").pack(anchor="w")



class TXControl(ResizingFrame):
  def __init__(self, parent):
    super().__init__(parent)

    self.config(relief="ridge", padding=(10,10,10,10))

    ttk.Label(self, text="Transmitter control (PlutoSDR)", font=bu_font).pack(anchor="w", pady=(0,10))

    # TX enable
    tx_enable = BooleanVar(value=False)
    ttk.Checkbutton(self, text="TX Enable", variable=tx_enable, command=lambda : print(tx_enable.get())).pack(anchor="w")

    ttk.Separator(self, orient=HORIZONTAL).pack(fill="x", pady=3)

    # Test sine
    cw_enable = BooleanVar(value=False)
    ttk.Checkbutton(self, text="Test CW transmission", variable=cw_enable, command=lambda : print(cw_enable.get())).pack(anchor="w")

    # set freq
    cw_freq_frame = ttk.Frame(self)
    cw_freq_frame.pack(anchor="w")
    cw_freq_offset = DoubleVar(value=300)
    cw_freq_offset_typing = DoubleVar(value=300)

    ttk.Label(cw_freq_frame, text="CW Frequency offset (Hz): ").grid(row=0, column=0)
    ttk.Label(cw_freq_frame, textvariable=cw_freq_offset).grid(row=0, column=1)
    ttk.Entry(cw_freq_frame, width=8, textvariable=cw_freq_offset_typing).grid(row=1, column=0)
    ttk.Button(cw_freq_frame, text="Set", 
               command=lambda : cw_freq_offset.set(cw_freq_offset_typing.get())
               ).grid(row=1, column=1)

    



class CommsControl(ResizingFrame):
  def __init__(self, parent):
    super().__init__(parent)

    self.config(relief="ridge", padding=(10,10,10,10))

    ttk.Label(self, text="Comms control", font=bu_font) \
       .grid(sticky="nw")


    # footer
    meowl = Image.open("images/meowl.png")
    meowl.thumbnail((100,100))
    meowl = ImageTk.PhotoImage(meowl)
    l = ttk.Label(self, image=meowl)
    l.grid(sticky="s")
    l.image = meowl

    ttk.Label(self, text="Made with <3 2026") \
        .grid(sticky="s")
 


  """
  def add_plot(self, x, y, title):
    # Create matplotlib figure
    fig, ax = plt.subplots(figsize=(5, 4))

    ax.plot(x, y)
    ax.set_title(title)
    ax.grid(True)

    # Put matplotlib figure into Tkinter
    figure_canvas = FigureCanvasTkAgg(
        fig,
        master=self.plot_frame
    )

    figure_canvas.draw()

    # Pack plots horizontally
    widget = figure_canvas.get_tk_widget()
    widget.pack(
        side="left",
        padx=10,
        pady=10
    )

    # Keep references alive
    self.figures.append(fig)
    self.canvases.append(figure_canvas)
  """


if __name__ == "__main__":
  gui = GUI()
  root.mainloop()