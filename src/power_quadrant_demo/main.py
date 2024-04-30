"""
The callable file of the project
"""

import logging

from controller import Controller

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    controller = Controller()
    controller.run()
