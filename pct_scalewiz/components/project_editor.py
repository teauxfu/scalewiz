"""Form for mutating Project objects."""
from __future__ import annotations

import os.path
import tkinter as tk
import typing
from tkinter import filedialog, ttk

from pct_scalewiz.components.base_frame import BaseFrame
from pct_scalewiz.components.project_info import ProjectInfo
from pct_scalewiz.components.project_params import ProjectParams
from pct_scalewiz.components.project_report import ProjectReport
from pct_scalewiz.models.project import Project

if typing.TYPE_CHECKING:
    from pct_scalewiz.models.test_handler import TestHandler


class ProjectEditor(BaseFrame):
    """Form for mutating Project objects.

    Has a tab control widget for separating the sub-forms.
    """

    def __init__(self, parent: tk.Toplevel, handler: TestHandler) -> None:
        BaseFrame.__init__(self, parent)
        self.handler = handler
        self.grid_columnconfigure(0, weight=1)
        if os.path.isfile(handler.project.path.get()):
            self.editorProject = Project.load_json(handler.project.path.get())
            self.editorProject.path.set(handler.project.path.get())
        else:
            self.editorProject = Project()
        self.build()

    def build(self) -> None:
        """Render the UI."""
        for child in self.winfo_children():
            child.destroy()

        tab_control = ttk.Notebook(self)
        tab_control.grid(row=0, column=0)

        tab_control.add(ProjectInfo(self), text="Project info")
        tab_control.add(ProjectParams(self), text="Experiment parameters")
        tab_control.add(ProjectReport(self), text="Report settings")

        button_frame = ttk.Frame(self)
        ttk.Button(
            button_frame, text="Save", width=7, command=lambda: self.save()
        ).grid(row=0, column=0, padx=5)
        ttk.Button(
            button_frame, text="Save as", width=7, command=lambda: self.save_as()
        ).grid(row=0, column=1, padx=10)
        ttk.Button(button_frame, text="New", width=7, command=lambda: self.new()).grid(
            row=0, column=2, padx=5
        )
        button_frame.grid(row=1, column=0)

    def render(self, label: tk.Widget, entry: tk.Widget, row: int) -> None:
        """Render the passed label and entry on the passed row."""
        # pylint: disable=no-self-use
        label.grid(row=row, column=0, sticky=tk.E)
        entry.grid(row=row, column=1, sticky=tk.E + tk.W, pady=1)

    def new(self) -> None:
        """Resets the form by connecting to a new Project."""
        self.editorProject = Project()
        self.build()

    def save(self) -> None:
        """Save the current Project to file as JSON."""
        if self.editorProject.path.get() == "":
            self.save_as()
        else:
            Project.dump_json(self.editorProject)
            self.handler.project = Project.load_json(self.editorProject.path.get())
            self.handler.parent.build()

    def save_as(self) -> None:
        """Saves the Project to JSON using a Save As dialog."""
        file_path = filedialog.asksaveasfilename(
            title="Save Project As:",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"{self.editorProject.name.get()}.json",
        )

        if file_path != "":
            # make sure it is JSON extension
            ext = file_path[-5:]
            if not ext in (".json", ".JSON"):
                file_path = f"{file_path}.json"
            self.editorProject.path.set(file_path)
            self.save()
