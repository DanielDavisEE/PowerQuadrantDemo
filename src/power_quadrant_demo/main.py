"""
The callable file of the project
"""

import logging
import tkinter as tk

from model import Model
from view import View

logging.basicConfig(level=logging.DEBUG)

matplotlib_logger = logging.getLogger('matplotlib')
matplotlib_logger.setLevel(logging.INFO)


class Controller:
    """
    The controller component of the MVC gui model
    """
    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.debug('Running __init__')

        self.root = tk.Tk()
        self.root.title("Power Quadrants")

        self.model = Model(self.root)
        self.view = View(self.root, self.model)
        self.view.setup()
        self.view.refresh()

        # Cause any updates to the model to be reflected by the view
        self.model.state_count.trace_add('write', lambda *_: self.view.refresh())

        # Configure window size and placement
        self.root.resizable(False, False)
        self.root.eval('tk::PlaceWindow . center')
        self.root.minsize(self.root.winfo_width(), self.root.winfo_height())

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    controller = Controller()
    controller.run()
