from tkinter import *
from tkinter import ttk
from tkinter import font

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure

import numpy as np

from PIL import Image, ImageTk


class GUI:
    def __init__(self):
      """
      exposed:
      self.rx_controls : RXControl
      self.tx_controls : TXControl
      self.rx_graphs : RXGraphs
      self.tx_graphs : TXGraphs
      """

      self.root = Tk()

      self.root.geometry("1600x800")
      self.root.title("super cool digital communications thing +_+")
      self.root.columnconfigure(0, weight=1)
      self.root.rowconfigure(0, weight=1)
      self.root.protocol("WM_DELETE_WINDOW", self.on_close)

      # fonts
      self.default_font = font.nametofont("TkDefaultFont")
      self.default_font.configure(size=12)
      self.bu_font = self.default_font.copy() # bold underline
      self.bu_font.configure(underline=True, weight="bold")
      self.u_font = self.default_font.copy() # underline
      self.u_font.configure(underline=True)
      self.b_font = self.default_font.copy() # bold
      self.b_font.configure(weight="bold")

      main_frame = ttk.Frame(self.root, padding=3)
      main_frame.grid(row=0, column=0, sticky="nsew")
      main_frame.rowconfigure([0,1], weight=1, uniform="rows")

      # red / blue titles
      ttk.Label(main_frame, text="TX", foreground="white", background="red", anchor="center") \
          .grid(row=1, column=0, sticky="nsew")
      ttk.Label(main_frame, text="RX", foreground="white", background="blue", anchor="center") \
          .grid(row=0, column=0, sticky="nsew")
      main_frame.columnconfigure(0, weight=0, minsize=50)

      # graphs
      self.rx_graphs = RXGraphs(self, main_frame)
      self.rx_graphs.grid(row=0, column=1, sticky="nsew")
      self.tx_graphs = TXGraphs(self, main_frame)
      self.tx_graphs.grid(row=1, column=1, sticky="nsew")
      main_frame.columnconfigure(1, weight=2)

      # controls
      self.rx_controls = RXControl(self, main_frame)
      self.rx_controls.grid(row=0, column=2, sticky="nsew")
      self.tx_controls = TXControl(self, main_frame)
      self.tx_controls.grid(row=1, column=2, sticky="nsew")
      main_frame.columnconfigure(2, weight=1)

      ttk.Separator(main_frame, orient=VERTICAL).grid(row=0, column=3, sticky="nsew", rowspan=2)
      main_frame.columnconfigure(3, weight=0)

      self.comms_control = CommsControl(self, main_frame)
      self.comms_control.grid(row=0, column=4, sticky="nsew", rowspan=2)
      main_frame.columnconfigure(4, weight=1)
      
      for child in main_frame.winfo_children():
        child.grid_configure(padx=4, pady=4)

      self.root.after(2000, lambda : print("a"))

    def on_close(self):
      self.root.quit()
      self.root.destroy()


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

    # update canvas when main_frame changes size
    self.main_frame.bind("<Configure>", self._update_scrollregion)

  def _update_scrollregion(self, event=None):
    self.canvas.configure(scrollregion=self.canvas.bbox("all"))

class HPlots(HScrollable):
  def __init__(self, gui, parent):
    super().__init__(parent)

    self.next_graph_col_i = 0
    self.figures = []
    self.canvases = []

  def add_plot(self, fig):
    # Put matplotlib figure into Tkinter
    figure_canvas = FigureCanvasTkAgg(
        fig,
        master=self.main_frame
    )

    figure_canvas.draw()

    # Pack plots horizontally
    widget = figure_canvas.get_tk_widget()
    widget.grid(row=0, column=self.next_graph_col_i, padx=10, pady=10)

    toolbar = NavigationToolbar2Tk(figure_canvas, self.main_frame, pack_toolbar=False)
    toolbar.grid(row=1, column=self.next_graph_col_i)
    toolbar.update()

    self.next_graph_col_i += 1

    # Keep references alive
    self.figures.append(fig)
    self.canvases.append(figure_canvas)
    
    return figure_canvas

    ### update
    #canvas.draw_idle() 



class RXGraphs(HPlots):
  def __init__(self, gui, parent):
    super().__init__(gui, parent)

    self.config(relief="ridge", padding=(10,10,10,10))

class TXGraphs(HPlots):
  def __init__(self, gui, parent):
    super().__init__(gui, parent)

    self.config(relief="ridge", padding=(10,10,10,10))


class RXControl(ResizingFrame):
  def __init__(self, gui, parent,
    live_rx_callback         = lambda a : None, # f(bool checked)
    single_rx_callback       = lambda   : None, # f()
    set_manaul_gain_callback = lambda a : None, # f(str val_db)
    set_auto_gain_callback   = lambda a : None,  # f(str value ["Manual", "Fast Attack", "Slow Attack"])
    probe_usb_callback       = lambda   : None,  # f()
  ):
    """
    interface out:
    self.measured_data_rate_percent : StringVar()

    self.live_rx_callback
    self.single_rx_callback
    self.set_manaul_gain_callback
    self.set_auto_gain_callback
    self.probe_usb_callback
    """
    super().__init__(parent)

    self.live_rx_callback         = live_rx_callback        
    self.single_rx_callback       = single_rx_callback      
    self.set_manaul_gain_callback = set_manaul_gain_callback
    self.set_auto_gain_callback   = set_auto_gain_callback  
    self.probe_usb_callback       = probe_usb_callback      

    self.config(relief="ridge", padding=(10,10,10,10))

    ttk.Label(self, text="Reciever control (PlutoSDR)", font=gui.bu_font) \
       .pack(anchor="w", pady=(0,10))

    # live rx
    b_live_rx = BooleanVar(value=False)
    ttk.Checkbutton(self, text="Live Receive", variable=b_live_rx, command=lambda : self.live_rx_callback(b_live_rx.get())).pack(anchor="w")

    # single rx
    ttk.Button(self, text="Single Receive", command=lambda : self.single_rx_callback()).pack(anchor="w")

    ttk.Separator(self, orient=HORIZONTAL).pack(fill="x", pady=3)

    ### rx gain
    # manual (packed after agc)
    rx_gain_frame = ttk.Frame(self)
    rx_manual_gain_label = ttk.Label(rx_gain_frame, text="Manual RX Gain (dB)")
    rx_manual_gain_label.pack(side="left")
    rx_gain_slider = Scale(rx_gain_frame, from_=0, to=74, orient=HORIZONTAL, command=lambda a : self.set_manaul_gain_callback(a))
    rx_gain_slider.set(20)
    rx_gain_slider.pack(side="left")

    selected_agc_mode = StringVar()
    def set_agc_mode(*args):
      if selected_agc_mode.get() == "Manual":
        rx_manual_gain_label.config(state="normal")
        rx_gain_slider.config(state="normal")
      else:
        rx_manual_gain_label.config(state="disabled")
        rx_gain_slider.config(state="disabled")
      self.set_auto_gain_callback(selected_agc_mode.get())

    rx_agc_frame = ttk.Frame(self)
    ttk.Label(rx_agc_frame, text="AGC setting").pack(side="left")
    agc_mode_selector = ttk.Combobox(rx_agc_frame, textvariable=selected_agc_mode, values=["Manual", "Fast Attack", "Slow Attack"], state="readonly")
    agc_mode_selector.current(0)
    agc_mode_selector.bind('<<ComboboxSelected>>', set_agc_mode)
    agc_mode_selector.pack(side="left")

    rx_agc_frame.pack(anchor="w")
    rx_gain_frame.pack(anchor="w")


    ttk.Separator(self, orient=HORIZONTAL).pack(fill="x", pady=3)

    # probe usb
    self.measured_data_rate_percent = StringVar()
    ttk.Button(self, text="Probe USB", command=lambda : self.probe_usb_callback()).pack(anchor="w")
    ttk.Label(self, text="% of max data rate: ").pack(anchor="w")
    ttk.Label(self, textvariable=self.measured_data_rate_percent).pack(anchor="w")

class TXControl(ResizingFrame):
  def __init__(self, gui, parent,
    tx_enable_callback     = lambda a : None, # f(bool checked)
    set_gain_callback      = lambda a : None, # f(str val)
    test_cw_check_callback = lambda a : None, # f(bool checked)
    set_cw_offset_callback = lambda a : None, # f(float freq)
  ):
    """
    interface out:
    self.tx_enable_callback
    self.set_gain_callback
    self.test_cw_check_callback
    self.set_cw_offset_callback
    """
    super().__init__(parent)

    self.tx_enable_callback     = tx_enable_callback
    self.set_gain_callback      = set_gain_callback
    self.test_cw_check_callback = test_cw_check_callback
    self.set_cw_offset_callback = set_cw_offset_callback

    self.config(relief="ridge", padding=(10,10,10,10))

    ttk.Label(self, text="Transmitter control (PlutoSDR)", font=gui.bu_font).pack(anchor="w", pady=(0,10))

    # TX enable
    tx_enable = BooleanVar(value=False)
    ttk.Checkbutton(self, text="TX Enable", variable=tx_enable, command=lambda : self.tx_enable_callback(tx_enable.get())).pack(anchor="w")

    ttk.Separator(self, orient=HORIZONTAL).pack(fill="x", pady=3)

    # tx gain
    tx_gain_frame = ttk.Frame(self)
    tx_gain_frame.pack(anchor="w")
    ttk.Label(tx_gain_frame, text="TX Gain (dB)").pack(side="left")
    tx_gain_slider = Scale(tx_gain_frame, from_=-90, to=0, orient=HORIZONTAL, command=lambda a: self.set_gain_callback(a))
    tx_gain_slider.set(-20)
    tx_gain_slider.pack(side="left")

    ttk.Separator(self, orient=HORIZONTAL).pack(fill="x", pady=3)

    # Test sine
    cw_enable = BooleanVar(value=False)
    ttk.Checkbutton(self, text="Test CW transmission", variable=cw_enable, command=lambda : self.test_cw_check_callback(cw_enable.get())).pack(anchor="w")

    # set freq
    cw_freq_frame = ttk.Frame(self)
    cw_freq_frame.pack(anchor="w")
    cw_freq_offset = DoubleVar(value=100000)
    cw_freq_offset_typing = DoubleVar(value=100000)

    ttk.Label(cw_freq_frame, text="CW Frequency offset (Hz): ").grid(row=0, column=0)
    ttk.Label(cw_freq_frame, textvariable=cw_freq_offset).grid(row=0, column=1)
    ttk.Entry(cw_freq_frame, width=8, textvariable=cw_freq_offset_typing).grid(row=1, column=0)
    def set_cw_offset():
      cw_freq_offset.set(cw_freq_offset_typing.get())
      self.set_cw_offset_callback(cw_freq_offset_typing.get())
    ttk.Button(cw_freq_frame, text="Set", command=set_cw_offset).grid(row=1, column=1)


class CommsControl(ResizingFrame):
  def __init__(self, gui, parent):
    super().__init__(parent)

    self.config(relief="ridge", padding=(10,10,10,10))

    ttk.Label(self, text="Comms control", font=gui.bu_font) \
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
 

if __name__ == "__main__":
  gui = GUI()
  gui.root.mainloop()