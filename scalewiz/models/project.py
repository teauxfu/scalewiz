"""Model object for a project. Provides a JSON/Tk mapping."""

from __future__ import annotations

import json
import logging
import tkinter as tk
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from scalewiz import CONFIG
from scalewiz.helpers.configuration import update_config
from scalewiz.helpers.sort_nicely import sort_nicely
from scalewiz.models.test import Test

if TYPE_CHECKING:
    from typing import List
    from uuid import UUID

LOGGER = logging.getLogger("scalewiz")


class Project:
    """Model object for a project. Provides a JSON/tkVar mapping."""

    # pylint: disable=too-many-instance-attributes

    def __init__(self) -> None:
        self.tests: List[Test] = []
        self.uuid: str = None  # hex string id
        # experiment parameters that affect score
        self.baseline = tk.IntVar()
        self.limit_minutes = tk.DoubleVar()
        self.limit_psi = tk.IntVar()
        self.interval_seconds = tk.DoubleVar()
        self.flowrate = tk.DoubleVar()
        self.uptake_seconds = tk.DoubleVar()
        # report stuff
        self.output_format = tk.StringVar()
        # metadata for reporting
        self.customer = tk.StringVar()
        self.submitted_by = tk.StringVar()
        self.client = tk.StringVar()
        self.field = tk.StringVar()
        self.sample = tk.StringVar()
        self.sample_date = tk.StringVar()
        self.received_date = tk.StringVar()
        self.completed_date = tk.StringVar()
        self.name = tk.StringVar()  # identifier for the project
        self.analyst = tk.StringVar()
        self.numbers = tk.StringVar()
        self.path = tk.StringVar()  # path to the project's JSON file
        self.notes = tk.StringVar()
        self.bicarbs = tk.DoubleVar()
        self.bicarbs_increased = tk.BooleanVar()
        self.calcium = tk.DoubleVar()
        self.chlorides = tk.DoubleVar()
        self.temperature = tk.DoubleVar()  # the test temperature
        self.plot = tk.StringVar()  # path to plot local file
        self.set_defaults()  # get default values from the config
        self.add_traces()  # these need to be cleaned up later

    def set_defaults(self) -> None:
        """Sets project parameters to the defaults read from the config file."""
        defaults = CONFIG["defaults"]
        # make sure we are seeing reasonable values
        for key, value in defaults.items():
            if not isinstance(value, str) and value < 0:
                defaults[key] = value * (-1)
        # apply values
        self.baseline.set(defaults["baseline"])
        self.interval_seconds.set(defaults["reading_interval"])
        self.limit_minutes.set(defaults["time_limit"])
        self.limit_psi.set(defaults["pressure_limit"])
        self.output_format.set(defaults["output_format"])
        self.temperature.set(defaults["test_temperature"])
        self.flowrate.set(defaults["flowrate"])
        self.uptake_seconds.set(defaults["uptake_time"])
        # this must never be <= 0
        if self.interval_seconds.get() <= 0:
            self.interval_seconds.set(1)
        self.analyst.set(CONFIG["recents"]["analyst"])

    def get_metadata(self) -> dict:
        """Returns a dict representing the Project's metadata.

        Returns:
            dict: represents the project's metadata
        """
        return {
            "customer": self.customer.get(),
            "submittedBy": self.submitted_by.get(),
            "productionCo": self.client.get(),
            "field": self.field.get(),
            "sample": self.sample.get(),
            "sampleDate": self.sample_date.get(),
            "recDate": self.received_date.get(),
            "compDate": self.completed_date.get(),
            "name": self.name.get(),
            "analyst": self.analyst.get(),
            "numbers": self.numbers.get(),
            "path": str(Path(self.path.get()).resolve()),
            "notes": self.notes.get(),
        }

    def get_params(self) -> dict:
        """Returns a dict representing the Project's experiment parameters.

        Returns:
            dict: a dict representing experiment parameters
        """
        return {
            "bicarbonates": self.bicarbs.get(),
            "bicarbsIncreased": self.bicarbs_increased.get(),
            "calcium": self.calcium.get(),
            "chlorides": self.chlorides.get(),
            "baseline": self.baseline.get(),
            "temperature": self.temperature.get(),
            "limitPSI": self.limit_psi.get(),
            "limitMin": self.limit_minutes.get(),
            "interval": self.interval_seconds.get(),
            "flowrate": self.flowrate.get(),
            "uptake": self.uptake_seconds.get(),
        }

    def dump_json(self, path: str = None) -> None:
        """Dump a JSON representation of the Project at the passed path."""
        if path is None:
            path = Path(self.path.get())

        blanks = {}
        trials = {}
        for test in self.tests:
            label = test.label.get().lower()
            while label in blanks or label in trials:  # make sure we don't overwrite
                label = "".join((label, " - copy"))
            test.label.set(label)
            if test.is_blank.get():
                blanks[label] = test
            else:
                trials[label] = test

        blank_labels = sort_nicely(list(blanks.keys()))
        trial_labels = sort_nicely(list(trials.keys()))
        tests = []
        for label in blank_labels:
            tests.append(blanks.pop(label))
        for label in trial_labels:
            tests.append(trials.pop(label))

        self.tests.clear()
        self.tests = [test for test in tests]

        this = {
            "info": self.get_metadata(),
            "params": self.get_params(),
            "tests": [test.to_dict() for test in self.tests],
            "outputFormat": self.output_format.get(),
            "plot": str(Path(self.plot.get()).resolve()),
        }
        try:
            with Path(path).open("w") as file:
                json.dump(this, file, indent=4)
            LOGGER.info("Saved %s to %s", self.name.get(), path)
            update_config("recents", "analyst", self.analyst.get())
            update_config("recents", "project", str(Path(self.path.get()).resolve()))
        except Exception as err:
            LOGGER.exception(err)

    def load_json(self, path: str) -> None:
        """Return a Project from a passed path to a JSON dump."""
        path = Path(path).resolve()
        if path.is_file():
            LOGGER.info("Loading from %s", path)
            with path.open("r") as file:
                obj = json.load(file)

        # we expect the data files to be shared over Dropbox, etc.
        if str(path) != obj["info"]["path"]:
            LOGGER.warning(
                "Opened a Project whose actual path didn't match its path property"
            )
            obj["info"]["path"] = str(path)
        self.uuid = UUID(obj.get("uuid", uuid4().hex))

        # clerical metadata
        info: dict = obj["info"]
        self.customer.set(info.get("customer"))
        self.submitted_by.set(info.get("submittedBy"))
        self.client.set(info.get("productionCo"))
        self.field.set(info.get("field"))
        self.sample.set(info.get("sample"))
        self.sample_date.set(info.get("sampleDate"))
        self.received_date.set(info.get("recDate"))
        self.completed_date.set(info.get("compDate"))
        self.name.set(info.get("name"))
        self.numbers.set(info.get("numbers"))
        self.analyst.set(info.get("analyst"))
        self.path.set(str(Path(info["path"]).resolve()))
        self.notes.set(info.get("notes"))
        # experimental metadata
        defaults = CONFIG["defaults"]
        params: dict = obj["params"]
        self.bicarbs.set(params.get("bicarbonates", 0))
        self.bicarbs_increased.set(params.get("bicarbsIncreased", False))
        self.calcium.set(params.get("calcium", 0))
        self.chlorides.set(params.get("chlorides", 0))
        self.baseline.set(params.get("baseline", defaults["baseline"]))
        self.temperature.set(params.get("temperature", defaults["test_temperature"]))
        self.limit_psi.set(params.get("limitPSI", defaults["pressure_limit"]))
        self.limit_minutes.set(params.get("limitMin", defaults["time_limit"]))
        self.interval_seconds.set(params.get("interval", defaults["reading_interval"]))
        self.flowrate.set(params.get("flowrate", defaults["flowrate"]))
        self.uptake_seconds.set(params.get("uptake", defaults["uptake_time"]))
        self.output_format.set(obj.get("outputFormat", defaults["output_format"]))
        self.plot.set(obj.get("plot"))

        self.tests.clear()
        for entry in obj.get("tests"):
            test = Test(data=entry)
            self.tests.append(test)

    # traces / validation stuff

    def add_traces(self) -> None:
        """Adds tkVar traces where needed. Must be cleaned up with remove_traces."""
        self.customer.trace_add("write", self.update_proj_name)
        self.client.trace_add("write", self.update_proj_name)
        self.field.trace_add("write", self.update_proj_name)
        self.sample.trace_add("write", self.update_proj_name)

    def remove_traces(self) -> None:
        """Remove tkVar traces to allow the GC to do its thing."""
        variables = (self.customer, self.client, self.field, self.sample)
        for var in variables:
            try:
                var.trace_remove("write", var.trace_info()[0][1])
            except IndexError:  # sometimes this spaghets when loading empty projects...
                pass
        for test in self.tests:
            test.remove_traces()

    def update_proj_name(self, *args) -> None:
        """Constructs a default name for the Project."""
        # extra unused args are passed in by tkinter
        if self.client.get() != "":
            name = self.client.get().strip()
        else:
            name = self.customer.get().strip()
        if self.field.get() != "":
            name = f"{name} - {self.field.get().strip()}"
        if self.sample.get() != "":
            name = f"{name} ({self.sample.get().strip()})"
        self.name.set(name)
