import logging
import tkinter as tk
from tkinter import ttk

import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import Figure

logging.basicConfig(level=logging.INFO)


class GUIBlock:
    root = tk.Tk()

    style = ttk.Style(root)
    style.configure('Header.TLabel', font=('Helvetica', 14))
    style.configure('SubHeader.TLabel', font=('Helvetica', 12))

    queue_refresh = tk.BooleanVar(root, name='QueueGraphRedraw')

    phi = tk.DoubleVar(root, name='GraphPhi', value=0.)

    # x_coord = tk.DoubleVar(root, name='GraphXCoord', value=1.)
    # y_coord = tk.DoubleVar(root, name='GraphYCoord', value=0.)

    def __init__(self, parent):
        super().__init__()

        self.frame = ttk.Frame(parent)
        self.children = []

        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(logging.DEBUG)

    def __getattr__(self, item):
        if item in {'pack', 'grid', 'place'}:
            pass_through_f = getattr(self.frame, item)
            return pass_through_f

    def refresh(self):
        for child in self.children:
            child.refresh()


class GraphBlock(GUIBlock):
    def __init__(self, parent):
        super().__init__(parent)

        parent.children.append(self)

        self.refresh()

    def _create_graph(self):
        fig = Figure(figsize=(5, 5), dpi=100)
        ax = fig.add_subplot(111)

        canvas = FigureCanvasTkAgg(fig, master=self.frame)  # A tk.DrawingArea.
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        toolbar = NavigationToolbar2Tk(canvas, self.frame, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(side=tk.TOP, fill=tk.BOTH, expand=False)

        # Assign to the class attribute so the other parts of the GUI can access them
        GUIBlock.ax = ax
        GUIBlock.canvas = canvas

    def refresh(self):
        super().refresh()

        for child in self.frame.winfo_children():
            child.destroy()

        self._create_graph()
        self._plot_graph()


class QuadrantViewer(GraphBlock):
    def _plot_graph(self):
        # Plot lines on graph
        phi_array = np.linspace(0, 2 * np.pi, 100)
        self.ax.plot(np.sin(phi_array), np.cos(phi_array), 'k')

        self.log.debug('Graph redraw complete')


class WaveformViewer(GraphBlock):

    def draw_graph(self):
        for child in self.frame.winfo_children():
            child.destroy()

        self._create_graph()

        # Plot lines on graph
        phi_array = np.linspace(0, 2 * np.pi, 100)
        self.ax.plot(np.sin(phi_array), 'r')

        self.queue_refresh.set(False)

        self.log.debug('Graph redraw complete')


class GraphOptionsPane(GUIBlock):

    def __init__(self, parent):
        super().__init__(parent)

        phi_scale_frame = ttk.Frame(self.frame)
        phi_scale_frame.pack(
            side=tk.TOP, fill=tk.BOTH, expand=False)
        phi_scale_frame.columnconfigure(1, weight=1)

        ttk.Label(phi_scale_frame, text='Phi').grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.LabeledScale(phi_scale_frame, self.phi, -np.pi, np.pi).grid(
            row=0, column=1, sticky=tk.EW, padx=5, pady=5)


class PowerQuadrantsGUI(GUIBlock):

    def __init__(self):
        super().__init__(self.root)

        self.root.wm_title("Power Quadrants")

        self.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # graph_viewer = GraphViewer(body_frame)
        # graph_viewer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.queue_refresh.trace_add('write', lambda *_: self.refresh_graphs() if self.queue_refresh.get() else None)

        QuadrantViewer(self.frame).pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=5, pady=5)
        WaveformViewer(self.frame).pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=5, pady=5)
        GraphOptionsPane(self.frame).pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=5, pady=5)

        self.root.resizable(False, False)
        self.root.eval('tk::PlaceWindow . center')
        self.root.minsize(self.root.winfo_width(), self.root.winfo_height())

    def refresh_graphs(self):
        self.refresh()

        self.queue_refresh.set(False)

    def mainloop(self):
        self.root.mainloop()


def power_quadrants_gui():
    gui = PowerQuadrantsGUI()
    gui.mainloop()


if __name__ == "__main__":
    power_quadrants_gui()
