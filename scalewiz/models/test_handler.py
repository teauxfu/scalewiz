"""Handles a test."""

from __future__ import annotations

import tkinter as tk
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from logging import DEBUG, FileHandler, Formatter, getLogger
from pathlib import Path
from queue import Queue
from time import sleep, time
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

from py_hplc import NextGenPump

import scalewiz
from scalewiz.models.project import Project
from scalewiz.models.test import Reading, Test

if TYPE_CHECKING:
    from logging import Logger
    from typing import List, Set, Union


class TestHandler:
    """Handles a Test."""

    # pylint: disable=too-many-instance-attributes

    def __init__(self, name: str = "Nemo") -> None:
        self.name = name
        self.root: tk.Tk = scalewiz.ROOT
        self.logger: Logger = getLogger(f"scalewiz.{name}")
        self.project: Project = Project()
        self.test: Test = None
        self.readings: List[Reading] = []
        self.max_readings: int = None  # max # of readings to collect
        self.limit_psi: int = None
        self.max_psi_1: int = None
        self.max_psi_2: int = None
        self.limit_minutes: float = None
        self.log_handler: FileHandler = None  # handles logging to log window
        # test handler view overwrites this attribute in the view's build()
        self.log_queue: Queue[str] = Queue()  # view pulls from this queue
        self.dev1 = tk.StringVar()
        self.dev2 = tk.StringVar()
        self.stop_requested: bool = bool()
        self.progress = tk.IntVar()
        self.elapsed_min: float = float()  # used for evaluations
        self.pump1: NextGenPump = None
        self.pump2: NextGenPump = None
        self.pool = ThreadPoolExecutor(max_workers=1)

        # UI concerns
        self.views: List[tk.Widget] = []  # list of views displaying the project
        self.is_running: bool = bool()
        self.is_done: bool = bool()
        self.new_test()

    @property
    def can_run(self) -> bool:
        """Returns a bool indicating whether or not the test can run."""
        return (
            (self.max_psi_1 < self.limit_psi or self.max_psi_2 < self.limit_psi)
            and self.elapsed_min < self.limit_minutes
            and len(self.readings) < self.max_readings
            and not self.stop_requested
        )

    def start_test(self) -> None:
        """Perform a series of checks to make sure the test can run, then start it."""
        issues = []
        if not Path(self.project.path.get()).is_file():
            msg = "Select an existing project file first"
            issues.append(msg)

        if self.test.name.get() == "":
            msg = "Name the experiment before starting"
            issues.append(msg)

        if self.test.name.get() in {test.name.get() for test in self.project.tests}:
            msg = "A test with this name already exists in the project"
            issues.append(msg)

        if self.test.clarity.get() == "" and not self.test.is_blank.get():
            msg = "Water clarity cannot be blank"
            issues.append(msg)

        self.update_log_handler(issues)

        # this method will append issue msgs if any occur
        self.setup_pumps(issues)  # hooray for pointers
        if len(issues) > 0:
            messagebox.showwarning("Couldn't start the test", "\n".join(issues))
            for pump in (self.pump1, self.pump2):
                pump.close()
        else:
            self.stop_requested = False
            self.is_done = False
            self.is_running = True
            self.rebuild_views()
            self.uptake_cycle()

    def uptake_cycle(self) -> None:
        """Get ready to take readings."""
        uptake = self.project.uptake_seconds.get()
        step = uptake / 100  # we will sleep for 100 steps
        self.pump1.run()
        self.pump2.run()
        rinse_start = time()
        for i in range(100):
            if self.can_run:
                self.progress.set(i)
                sleep(step - ((time() - rinse_start) % step))
            else:
                self.stop_test(save=False)
                break
        # we use these in the loop
        self.pool.submit(self.take_readings)

    def take_readings(self) -> None:
        interval = self.project.interval_seconds.get()
        start_time = time()
        # readings loop ----------------------------------------------------------------
        while self.can_run:
            minutes_elapsed = (time() - start_time) / 60

            psi1 = self.pump1.pressure
            psi2 = self.pump2.pressure
            average = round(((psi1 + psi2) / 2))

            reading = Reading(
                elapsedMin=minutes_elapsed, pump1=psi1, pump2=psi2, average=average
            )

            # make a message for the log in the test handler view
            msg = "@ {:.2f} min; pump1: {}, pump2: {}, avg: {}".format(
                minutes_elapsed, psi1, psi2, average
            )
            self.log_queue.put(msg)
            self.logger.debug(msg)
            self.readings.append(reading)
            self.elapsed_min = minutes_elapsed
            self.logger.warn("%s / %s", len(self.readings), self.max_readings)
            prog = round((len(self.readings) / self.max_readings) * 100)
            self.progress.set(prog)

            if psi1 > self.max_psi_1:
                self.max_psi_1 = psi1
            if psi2 > self.max_psi_2:
                self.max_psi_2 = psi2

            # TYSM https://stackoverflow.com/a/25251804
            self.logger.warn("%s", interval - ((time() - start_time) % interval))
            sleep(interval - ((time() - start_time) % interval))
        else:
            self.stop_test(save=True)

    # logging stuff / methods that affect UI
    def new_test(self) -> None:
        """Initialize a new test."""
        self.logger.info("Initializing a new test")
        if isinstance(self.test, Test):
            self.test.remove_traces()
        self.test = Test()
        self.readings.clear()
        self.limit_psi = self.project.limit_psi.get()
        self.limit_minutes = self.project.limit_minutes.get()
        self.max_psi_1, self.max_psi_2 = 0, 0
        self.is_running, self.is_done = False, False
        self.progress.set(0)
        self.max_readings = round(
            self.project.limit_minutes.get() * 60 / self.project.interval_seconds.get()
        )
        self.rebuild_views()

    def setup_pumps(self, issues: List[str] = None) -> None:
        """Set up the pumps with some default values.
        Appends errors to the passed list
        """
        if issues is None:
            issues = []

        if self.dev1.get() in ("", "None found"):
            issues.append("Select a port for pump 1")

        if self.dev2.get() in ("", "None found"):
            issues.append("Select a port for pump 2")

        if self.dev1.get() == self.dev2.get():
            issues.append("Select two unique ports")
        else:
            self.pump1 = NextGenPump(self.dev1.get(), self.logger)
            self.pump2 = NextGenPump(self.dev2.get(), self.logger)

        for pump in (self.pump1, self.pump2):
            if pump is None or not pump.is_open:
                issues.append(f"Couldn't connect to {pump.serial.name}")
                continue
            pump.flowrate = self.project.flowrate.get()
            self.logger.info("Set flowrates to %s", pump.flowrate)

    def request_stop(self) -> None:
        """Requests that the Test stop."""
        if self.is_running:
            self.stop_requested = True

    def stop_test(self, save: bool = False, rinsing: bool = False) -> None:
        """Stops the pumps, closes their ports."""
        for pump in (self.pump1, self.pump2):
            if pump.is_open:
                pump.stop()
                pump.close()
                self.logger.info(
                    "Stopped and closed the device @ %s",
                    pump.serial.name,
                )

        if not rinsing:
            self.is_done = True
            self.is_running = False
            self.logger.warn("Test for %s has been stopped", self.test.name.get())
            for _ in range(3):
                self.views[0].bell()
        if save:
            self.save_test()

        self.rebuild_views()

    def save_test(self) -> None:
        """Saves the test to the Project file in JSON format."""
        self.logger.warn("TRYING TO SAVE")
        self.test.readings.extend(self.readings)
        self.logger.warn(
            "saved %s readings to %s", len(self.test.readings), self.test.name.get()
        )
        self.project.tests.append(self.test)
        self.project.dump_json()

        # refresh data / UI
        self.load_project(path=self.project.path.get(), new_test=False)

    def rebuild_views(self) -> None:
        """Rebuild all open Widgets that display or modify the Project file."""
        for widget in self.views:
            if widget.winfo_exists():
                self.logger.debug("Rebuilding %s", widget)
                self.root.after_idle(widget.build, {"reload": True})
            else:
                self.logger.debug(
                    "Removing dead widget %s", widget
                )  # clean up as we go
                self.views.remove(widget)

        self.logger.debug("Rebuilt all view widgets")

    def update_log_handler(self, issues: List[str]) -> None:
        """Sets up the logging FileHandler to the passed path."""
        id = "".join(char for char in self.test.name.get() if char.isalnum())
        log_file = f"{time():.0f}_{id}_{date.today()}.txt"
        parent_dir = Path(self.project.path.get()).parent.resolve()
        logs_dir = parent_dir.joinpath("logs").resolve()
        if not logs_dir.is_dir():
            logs_dir.mkdir()
        log_path = Path(logs_dir).joinpath(log_file).resolve()
        self.log_handler = FileHandler(log_path)

        formatter = Formatter(
            "%(asctime)s - %(thread)d - %(levelname)s - %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
        if self.log_handler in self.logger.handlers:  # remove the old one
            self.logger.removeHandler(self.log_handler)
        self.log_handler.setFormatter(formatter)
        self.log_handler.setLevel(DEBUG)
        self.logger.addHandler(self.log_handler)
        self.logger.info("Set up a log file at %s", log_file)
        self.logger.info("Starting a test for %s", self.project.name.get())

    def load_project(
        self,
        path: Union[str, Path] = None,
        loaded: Set[Path] = [],
        new_test: bool = True,
    ) -> None:
        """Opens a file dialog then loads the selected Project file.

        `loaded` gets built from scratch every time it is passed in -- no need to update
        """
        if path is None:
            path = filedialog.askopenfilename(
                initialdir='C:"',
                title="Select project file:",
                filetypes=[("JSON files", "*.json")],
            )
        if isinstance(path, str):
            path = Path(path).resolve()

        # check that the dialog succeeded, the file exists, and isn't already loaded
        if path.is_file():
            if path in loaded:
                msg = "Attempted to load an already-loaded project"
                self.logger.warning(msg)
                messagebox.showwarning("Project already loaded", msg)
            else:
                self.project.remove_traces()
                self.project = Project()
                self.project.load_json(path)
                if new_test:
                    self.new_test()
                self.logger.info("Loaded %s", self.project.name.get())
                self.rebuild_views()
