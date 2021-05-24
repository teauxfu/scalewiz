"""A table view to be displayed in the Evaluation Window."""

from __future__ import annotations
from scalewiz.helpers.score import score

import tkinter as tk
from logging import Logger, getLogger
from tkinter import ttk, messagebox
from tkinter.font import Font
from typing import TYPE_CHECKING

from scalewiz.components.test_evaluation_row import TestResultRow

if TYPE_CHECKING:
    from scalewiz.models.project import Project
    from scalewiz.models.test import Test
    from typing import List


LOGGER: Logger = getLogger("scalewiz")


class EvaluationDataView(ttk.Frame):
    """A widget for selecting devices."""

    def __init__(
        self,
        parent: ttk.Frame,
        project: Project,
    ) -> None:
        super().__init__(parent)
        
        self.eval_window = parent.master
        self.project = project
        self.trials: List[Test] = []
        self.blanks: List[Test] = []
        self.bold_font: Font = Font(family="Arial", weight="bold", size=10)
        self.build()

    
    def build(self) -> None:
        for child in self.winfo_children():
            child.destroy()
        self.sort_tests()
        
        self.apply_col_headers() # row 0
        # add blanks block
        blanks_lbl = ttk.Label(self, text='Blanks:', font=self.bold_font)
        blanks_lbl.grid(row=1, column=0, sticky='w') 
        for i, blank in enumerate(self.blanks):
            self.apply_test_row(blank, i+2) # skips rows for headers
        # add trials block
        len_blanks = len(self.blanks)
        trials_lbl = ttk.Label(self, text='Trials:', font=self.bold_font)
        trials_lbl.grid(row=len_blanks + 3, sticky='w') # skips rows for headers
        for i, trial in enumerate(self.trials):
            self.apply_test_row(trial, i+len_blanks+4)# skips rows for headers

    def apply_col_headers(self) -> None:
        labels = []
        labels.append(
            tk.Label(
                self,
                text="Name",
                font=self.bold_font,
                anchor='w',
            )
        )
        labels.append(
            tk.Label(self, text="Label", font=self.bold_font, width=20, anchor='w')
        )
        labels.append(
            tk.Label(
                self,
                text="Minutes",
                font=self.bold_font,
                anchor='center',
            )
        )
        labels.append(tk.Label(self, text="Pump", font=self.bold_font, anchor='center'))
        labels.append(
            tk.Label(self, text="Baseline PSI", font=self.bold_font, anchor='center')
        )
        labels.append(tk.Label(self, text="Max PSI", font=self.bold_font, anchor='center'))
        labels.append(
            tk.Label(self, text="Water Clarity", font=self.bold_font, anchor='center')
        )
        labels.append(
            tk.Label(self, text="Notes", font=self.bold_font, anchor='w')
        )
        labels.append(
            tk.Label(self, text="Score", font=self.bold_font, anchor='w')
        )
        labels.append(
            tk.Label(self, text="On Report", font=self.bold_font, anchor='w')
        )
        labels.append(tk.Label(self, text=" ", font=self.bold_font, anchor='w'))

        for i, lbl in enumerate(labels):
            self.grid_columnconfigure(i, weight=1)
            if i in (0, 1, 7):
                lbl.grid(row=0, column=i, padx=0, sticky='w')
            else:
                lbl.grid(row=0, column=i, padx=3, sticky="ew")


    def apply_test_row(self, test, row) -> None:
        """Creates a row for the test and grids it."""
        cols: List[tk.Widget] = []
        vcmd = self.register(self.update_score)
        # col 0 - name
        cols.append(ttk.Label(self, textvariable=test.name))
        # col 1 - label
        cols.append(
            ttk.Entry(
                self,
                textvariable=test.label,
                validate="focusout",
                validatecommand=vcmd,
                width=30
            )
        )
        # col 2 - duration
        duration = round(
            len(test.readings) * self.project.interval_seconds.get() / 60, 2
        )
        cols.append(
            ttk.Label(
                self,
                text=f"{duration:.2f}",
                anchor="center",
            )
        )
        # col 3 - pump to score
        to_score = ttk.Combobox(
            self,
            textvariable=test.pump_to_score,
            values=["pump 1", "pump 2", "average"],
            state="readonly",
            width=7,
            validate="all",
            validatecommand=vcmd,
        )
        to_score.bind("<MouseWheel>", self.update_score)
        cols.append(to_score)
        # col 4 - obs baseline
        cols.append(
            ttk.Label(
                self,
                textvariable=test.observed_baseline,
                anchor="center",
                width=5
            )
        )
        # col 5 - max psi
        cols.append(
            ttk.Label(
                self,
                textvariable=test.max_psi,
                anchor="center",
                width=7
            )
        )
        # col 6 - clarity
        cols.append(
            ttk.Label(
                self,
                textvariable=test.clarity,
                anchor="center",
            )
        )
        # col 7 - notes
        cols.append(ttk.Entry(self, textvariable=test.notes, width=30))
        # col 8 - result
        cols.append(
            ttk.Label(self, textvariable=test.result, width=5, anchor="center")
        )
        # col 9 - include on report
        cols.append(
            ttk.Checkbutton(
                self,
                variable=test.include_on_report,
                command=self.update_score,
            )
        )
        # col 10 - delete
        delete = lambda: self.remove_from_project(test)
        cols.append(
            ttk.Button(
                self,
                command=delete,
                text="Delete",
                width=7,
            )
        )

        for i, col in enumerate(cols):
            if i == 0:  # left align the name col
                col.grid(row=row, column=i, padx=1, pady=1, sticky="w")
            elif i == 7: # make the notes col stretch
                col.grid(row=row, column=i, padx=1, pady=1, sticky='ew')
            elif i == 10:
                col.grid(row=row, column=i, padx=(5, 0), pady=1, sticky='e')
            else:  
                col.grid(row=row, column=i, padx=1, pady=1)

    def sort_tests(self) -> None:
        """
        Sort through the editor_project, populating the lists of blanks and trials.
        """
        self.blanks.clear()
        self.trials.clear()

        for test in self.project.tests:
            if test.is_blank.get():
                self.blanks.append(test)
            else:
                self.trials.append(test)


    def remove_from_project(self, test: Test) -> None:
        """Removes a Test from the parent Project, then rebuilds the UI."""
        msg = (
            "You are about to delete {} from {}.\n"
            "This will become permanent once you save the project.\n"
            "Do you wish to continue?"
        ).format(test.name.get(), self.project.name.get())
        remove = messagebox.askyesno("Delete test", msg)
        if remove and test in self.project.tests:
            self.project.tests.remove(test)
            self.update_score()
            self.build()

    def update_score(self, *args) -> True:
        """Method to call score from a validation callback. Doesn't check anything."""
        # prevents a race condition when setting the score
        self.after(0, score(self.project, self.eval_window.log_text))
        return True