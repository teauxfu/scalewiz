from __future__ import annotations

import tkinter as tk
from logging import Logger, getLogger
from tkinter import ttk
from typing import TYPE_CHECKING

from serial.tools import list_ports

if TYPE_CHECKING:
    from typing import List

LOGGER: Logger = getLogger("scalewiz")


class DeviceBoxes(ttk.Frame):
    """A widget for selecting devices."""

    def __init__(
        self, parent: ttk.Frame, dev1: tk.StringVar, dev2: tk.StringVar
    ) -> None:
        super().__init__(parent)
        self.parent: ttk.Frame = parent
        self.devices_list: List[str] = []
        self.dev1: tk.StringVar = dev1
        self.dev2: tk.StringVar = dev2
        self.build()

    def build(self) -> None:
        """Builds the widget."""
        # let the widgets grow to fill
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        # make the widgets
        label = ttk.Label(self, text="     Devices:", anchor="e")
        self.device1_entry = ttk.Combobox(
            self,
            width=15,
            textvariable=self.dev1,
            values=self.devices_list,
            validate="all",
            validatecommand=self.update_devices_list,
        )
        self.device2_entry = ttk.Combobox(
            self,
            width=15,
            textvariable=self.dev2,
            values=self.devices_list,
            validate="all",
            validatecommand=self.update_devices_list,
        )
        # grid the widgets
        label.grid(row=0, column=0, sticky="ne")
        self.device1_entry.grid(row=0, column=1, sticky="w")
        self.device2_entry.grid(row=0, column=2, sticky="e")
        # refresh
        self.update_devices_list()

    def update_devices_list(self, *args) -> None:
        """Updates the devices list."""
        # extra unused args are passed in by tkinter
        self.devices_list = sorted([i.device for i in list_ports.comports()])
        if len(self.devices_list) < 1:
            self.devices_list = ["None found"]

        self.device1_entry.configure(values=self.devices_list)
        self.device2_entry.configure(values=self.devices_list)

        if len(self.devices_list) > 1:
            self.device1_entry.current(0)
            self.device2_entry.current(1)

        if "None found" not in self.devices_list:
            LOGGER.debug(
                "%s found devices: %s", self.parent.handler.name, self.devices_list
            )
