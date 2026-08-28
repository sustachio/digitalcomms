from tkinter import *
from tkinter import ttk

from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
# Implement the default Matplotlib key bindings.
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure

import numpy as np

class GUI:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1200x800")
        self.root.title("super cool digital communications thing +_+")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self.root, padding=3)
        main_frame.grid(row=0, column=0, sticky="nsew")

        ##### Left titles #####
        ttk.Label(main_frame, text="TX", foreground="white", background="red", anchor="center") \
           .grid(row=0, column=0, sticky="nsew")
        ttk.Label(main_frame, text="RX", foreground="white", background="blue", anchor="center") \
           .grid(row=1, column=0, sticky="nsew")

        ##### TX graphs #####
        tx_graphs = ttk.Frame(main_frame, relief="ridge", padding=10)
        tx_graphs      .grid(row=0, column=1, sticky="nsew")

        ttk.Label(tx_graphs, text="hello!!!!").pack(side="top", fill="x")
        ttk.Label(tx_graphs, text="hiii!!!!") .pack(side="top", fill="x")

        ##### TX connection #####
        tx_conn = ttk.Frame(main_frame, relief="ridge", padding=10)
        tx_conn      .grid(row=0, column=2, sticky="nsew")

        ##### RX graphs #####
        rx_graphs = ttk.Frame(main_frame, relief="ridge", padding=10)
        rx_graphs      .grid(row=1, column=1, sticky="nsew")

        plots = ScrollablePlots(rx_graphs)
        plots.grid(row=0, column=0, sticky="nsew")
        plots.add_plot()
        plots.add_plot()
        plots.add_plot()

        rx_graphs.rowconfigure(0, weight=1)
        rx_graphs.columnconfigure(0, weight=1)

        ##### RX connection #####
        rx_conn = ttk.Frame(main_frame, relief="ridge", padding=10)
        rx_conn      .grid(row=1, column=2, sticky="nsew")

        ####### Right area ########
        ttk.Separator(main_frame, orient=VERTICAL).grid(row=0, column=3, sticky="nsew", rowspan=2)
        
        command_section = ttk.Frame(main_frame, relief="ridge", padding=10)
        command_section      .grid(row=0, column=4, sticky="nsew", rowspan=2)

        ##########################

        main_frame.rowconfigure([0,1], weight=1, uniform="rows")

        main_frame.columnconfigure(0, weight=0, minsize=50)
        main_frame.columnconfigure(1, weight=2)
        main_frame.columnconfigure(2, weight=1)
        main_frame.columnconfigure(3, weight=0)
        main_frame.columnconfigure(4, weight=1)

        for child in main_frame.winfo_children():
          child.grid_configure(padx=4, pady=4)

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
    
    def ui_matplot(self, parent):
        fig = Figure(figsize=(5, 4), dpi=100)
        t = np.arange(0, 3, .01)
        fig.add_subplot(111).plot(t, 2 * np.sin(2 * np.pi * t))

        canvas = FigureCanvasTkAgg(fig, master=parent)  # A tk.DrawingArea.
        canvas.draw()
        canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)

        toolbar = NavigationToolbar2Tk(canvas, parent)
        toolbar.update()
        canvas.get_tk_widget().pack(side=TOP, fill=BOTH, expand=1)

class ScrollablePlots(Frame):
  def __init__(self, parent):
    super().__init__(parent)
    
    self.canvas = Canvas(self)
    self.scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)

    self.canvas.configure(xscrollcommand=self.scrollbar.set)

    self.canvas   .pack(side="top",    fill="both", expand=True)
    self.scrollbar.pack(side="bottom", fill="x")

    # where graphs go
    self.plot_frame = Frame(self.canvas)
    self.canvas_window = self.canvas.create_window((0,0), window=self.plot_frame, anchor="nw")

    # update canvas when plot_frame changes size
    self.plot_frame.bind("<Configure>", self._update_scrollregion)

  def _update_scrollregion(self, event=None):
    self.canvas.configure(scrollregion=self.canvas.bbox("all"))

  def add_plot(self):
    Label(self.plot_frame, text="hiii"*100).pack(side="left")

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



root = Tk()
gui = GUI(root)
gui.mainloop()
