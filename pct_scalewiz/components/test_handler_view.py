"""A Tkinter widget for handling tests."""
from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk
import typing

import matplotlib.pyplot as plt
import serial.tools.list_ports as list_ports

from pct_scalewiz.components.base_frame import BaseFrame
from pct_scalewiz.components.live_plot import LivePlot

if typing.TYPE_CHECKING:
    from pct_scalewiz.models.test_handler import TestHandler

logger = logging.getLogger("scalewiz")

# todo #1 these frames should probably be separated into separate classes


class TestHandlerView(BaseFrame):
    """A form for setting up / running Tests."""

    def __init__(self, parent: BaseFrame, handler: TestHandler) -> None:
        BaseFrame.__init__(self, parent)
        self.parent = parent
        self.handler = handler
        self.handler.parent = self
        self.devices_list = []
        self.build()

    def set_bindings(self) -> None:
        """Sets tkVar bindings for attributes on the current TestHandler."""
        self.handler.test.is_blank.trace(
            "w", self.update_test_type
        )  # might have to retrace on new test
        self.handler.is_running.trace("w", self.update_input_frame)
        self.handler.is_done.trace("w", self.update_init_btn)
        self.handler.dev1.trace("w", self.update_devices_list)
        self.handler.dev2.trace("w", self.update_devices_list)

    def build(self) -> None:
        """Builds the UI, destroying any currently existing widgets."""
        for child in self.winfo_children():
            child.destroy()

        self.set_bindings()
        self.inputs = []
        self.inputs_frame = ttk.Frame(self)
        self.inputs_frame.grid(row=0, column=0, sticky="new")
        # row 0 ---------------------------------------------------------------
        devices_label = ttk.Label(self.inputs_frame, text="      Devices:")
        devices_label.bind("<Button-1>", lambda _: self.update_devices_list())

        # put the boxes in a frame to make life easier
        frm = ttk.Frame(self.inputs_frame)  # this frame will set the width for the col
        self.device1_entry = ttk.Combobox(
            frm, width=15, textvariable=self.handler.dev1, values=self.devices_list
        )
        self.device2_entry = ttk.Combobox(
            frm, width=15, textvariable=self.handler.dev2, values=self.devices_list
        )
        self.device1_entry.grid(row=0, column=0, sticky=tk.W)
        self.device2_entry.grid(row=0, column=1, sticky=tk.E, padx=(4, 0))
        self.inputs.append(self.device1_entry)
        self.inputs.append(self.device2_entry)
        self.render(devices_label, frm, 0)

        # row 1 ---------------------------------------------------------------
        lbl = ttk.Label(self.inputs_frame, text="Project:")
        btn = ttk.Label(
            self.inputs_frame, textvariable=self.handler.project.name, anchor="center"
        )
        self.inputs.append(btn)
        self.render(lbl, btn, 1)

        # row 2 ---------------------------------------------------------------
        lbl = ttk.Label(self.inputs_frame, text="Test Type:")
        frm = ttk.Frame(self.inputs_frame)
        frm.grid_columnconfigure(0, weight=1)
        frm.grid_columnconfigure(1, weight=1)
        blank_radio = ttk.Radiobutton(
            frm, text="Blank", variable=self.handler.test.is_blank, value=True
        )
        blank_radio.grid(row=0, column=0)
        trial_radio = ttk.Radiobutton(
            frm, text="Trial", variable=self.handler.test.is_blank, value=False
        )
        trial_radio.grid(row=0, column=1)
        self.inputs.append(blank_radio)
        self.inputs.append(trial_radio)
        self.render(lbl, frm, 2)

        # row 3 ---------------------------------------------------------------
        self.grid_rowconfigure(3, weight=1)
        # row 3a ---------------------------------------------------------------
        self.trial_label_frame = ttk.Frame(self.inputs_frame)
        ttk.Label(self.trial_label_frame, text="Chemical:").grid(
            row=0, column=0, sticky=tk.E, pady=1
        )
        ttk.Label(self.trial_label_frame, text="Rate (ppm):").grid(
            row=1, column=0, sticky=tk.E, pady=1
        )
        ttk.Label(self.trial_label_frame, text="Clarity:").grid(
            row=2, column=0, sticky=tk.E, pady=1
        )

        self.trial_entry_frame = ttk.Frame(self.inputs_frame)
        self.trial_entry_frame.grid_columnconfigure(0, weight=1)
        chemical_entry = ttk.Entry(
            self.trial_entry_frame, textvariable=self.handler.test.chemical
        )
        chemical_entry.grid(row=0, column=0, sticky="ew", pady=1)
        rate_entry = ttk.Spinbox(
            self.trial_entry_frame,
            textvariable=self.handler.test.rate,
            from_=0,
            to=999999,
        )
        rate_entry.grid(row=1, column=0, sticky="ew", pady=1)
        clarity_options = ["Clear", "Slightly hazy", "Hazy"]
        clarity_entry = ttk.Combobox(
            self.trial_entry_frame,
            values=clarity_options,
            textvariable=self.handler.test.clarity,
        )
        clarity_entry.grid(row=2, column=0, sticky="ew", pady=1)
        clarity_entry.current(0)

        self.inputs.append(chemical_entry)
        self.inputs.append(rate_entry)
        self.inputs.append(clarity_entry)

        # row 3b ---------------------------------------------------------------
        self.blank_label = ttk.Label(self.inputs_frame, text="Name:")
        self.blank_entry = ttk.Entry(self.inputs_frame, textvariable=self.handler.test.name)
        self.inputs.append(self.blank_entry)

        # row 4 ---------------------------------------------------------------
        lbl = ttk.Label(self.inputs_frame, text="Notes:")
        ent = ttk.Entry(self.inputs_frame, textvariable=self.handler.test.notes)
        self.inputs.append(ent)
        self.render(lbl, ent, 4)

        # iFrm end ------------------------------------------------------------

        # row 1 ---------------------------------------------------------------
        frm = ttk.Frame(self)
        self.start_button = ttk.Button(
            frm, text="Start", command=lambda: self.handler.start_test()
        )
        stop_button = ttk.Button(
            frm, text="Stop", command=lambda: self.handler.request_stop()
        )
        details_button = ttk.Button(
            frm, text="Toggle Details", command=lambda: self.update_plot_visible()
        )

        self.start_button.grid(row=0, column=0)
        stop_button.grid(row=0, column=1)
        details_button.grid(row=0, column=2)

        ttk.Progressbar(frm, variable=self.handler.progress).grid(
            row=1, columnspan=3, sticky="nwe"
        )
        self.elapsed_label = ttk.Label(frm, textvariable=self.handler.elapsed)
        self.elapsed_label.grid(row=1, column=1)
        frm.grid(row=1, column=0, padx=1, pady=1, sticky="n")
        self.new_button = ttk.Button(
            frm, text="New", command=lambda: self.handler.new_test()
        )

        # rows 0-1 -------------------------------------------------------------
        # close all pyplots to prevent memory leak
        plt.close("all")
        self.plot_frame = LivePlot(self, self.handler)
        self.grid_columnconfigure(1, weight=1)  # let it grow
        self.grid_rowconfigure(1, weight=1)

        # row 2 ---------------------------------------------------------------
        self.log_frame = ttk.Frame(self)
        self.log_text = tk.scrolledtext.ScrolledText(
            self.log_frame, background="white", height=5, width=44, state="disabled"
        )
        # todo alert alert this is not elegant
        self.handler.log_text = self.log_text  # this is bad ?
        self.log_text.grid(sticky="ew")

        self.update_test_type()
        self.update_init_btn()
        self.update_devices_list()

    # methods to update local state

    def render(self, label, entry, row) -> None:
        """Renders a row on the UI. As method for convenience."""
        label.grid(row=row, column=0, sticky=tk.N + tk.E)
        entry.grid(row=row, column=1, sticky=tk.N + tk.E + tk.W, pady=1, padx=1)

    # todo shouldn't this be held by the test handler?
    def update_devices_list(self, *args) -> None:
        """Updates the devices list held by the TestHandler."""
        self.devices_list = sorted([i.device for i in list_ports.comports()])
        if len(self.devices_list) < 1:
            self.devices_list = ["None found"]
        self.device1_entry.configure(values=self.devices_list)
        self.device2_entry.configure(values=self.devices_list)
        if not "None found" in self.devices_list:
            logger.info("%s found devices: %s", self.handler.name, self.devices_list)

    def update_input_frame(self, *args) -> None:
        """Disables widgets in the input frame if a Test is running."""
        for child in self.inputs:
            if self.handler.is_running.get():
                child.configure(state="disabled")
            else:
                child.configure(state="normal")

    def update_init_btn(self, *args) -> None:
        """Changes the "Start" button to a "New" button when the Test finishes."""
        if self.handler.is_done.get():
            self.start_button.grid_remove()
            self.new_button.grid(row=0, column=0)
        else:
            self.new_button.grid_remove()
            self.start_button.grid(row=0, column=0)

    def update_test_type(self, *args):
        """Rebuilds part of the UI to change the entries wrt Test type (blank/trial)."""
        if self.handler.test.is_blank.get():
            self.trial_label_frame.grid_remove()
            self.trial_entry_frame.grid_remove()
            self.render(self.blank_label, self.blank_entry, 3)
            logger.info("%s: changed to Blank mode", self.handler.name)
        else:
            self.blank_label.grid_remove()
            self.blank_entry.grid_remove()
            self.render(self.trial_label_frame, self.trial_entry_frame, 3)
            logger.info("%s: changed to Trial mode", self.handler.name)

    def update_plot_visible(self) -> None:
        """Updates whether or not the details view is displayed across all TestHandlerViews."""
        is_visible = bool()
        # check if the plot is gridded
        if self.plot_frame.grid_info() != {}:
            is_visible = True

        for tab in self.parent.tabs():
            this = self.parent.nametowidget(tab)
            if not is_visible:  # show the details view
                logger.info("%s: Showing details view", this.handler.name)
                this.pltFrm.grid(row=0, column=1, rowspan=3)
                this.logFrm.grid(row=2, column=0, sticky="ew")
            else:  # hide the details view
                logger.info("%s: Hiding details view", this.handler.name)
                this.pltFrm.grid_remove()
                this.logFrm.grid_remove()
