"""Graphical interface for the FileZipper utility."""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Iterable, List

if __package__ in {None, ""}:  # pragma: no cover - exercised via script execution
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from filezipper.zipper import copy_to_locations, create_archive


@dataclass
class SelectionList:
    """Helper container for managing a list of filesystem selections."""

    values: List[str]
    listbox: tk.Listbox

    def add(self, new_values: Iterable[str]) -> None:
        for value in new_values:
            normalized = str(Path(value).expanduser())
            if normalized not in self.values:
                self.values.append(normalized)
                self.listbox.insert(tk.END, normalized)

    def remove_selected(self) -> None:
        selections = list(self.listbox.curselection())
        for index in reversed(selections):
            self.listbox.delete(index)
            del self.values[index]

    def clear(self) -> None:
        self.listbox.delete(0, tk.END)
        self.values.clear()


class FileZipperApp:
    """Tkinter application for creating archives and copying them to destinations."""

    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("FileZipper")
        root.geometry("720x520")

        self.sources_list = SelectionList([], self._create_listbox("Sources", row=0))
        self.destinations_list = SelectionList([], self._create_listbox("Cloud Destinations", row=2))

        self.include_hidden = tk.BooleanVar(value=False)
        self.output_path = tk.StringVar()

        self._build_controls()
        self._build_status_area()

    # ------------------------------------------------------------------ UI --
    def _create_listbox(self, title: str, row: int) -> tk.Listbox:
        frame = ttk.LabelFrame(self.root, text=title)
        frame.grid(row=row, column=0, padx=12, pady=8, sticky="nsew")
        self.root.grid_rowconfigure(row, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        listbox = tk.Listbox(frame, selectmode=tk.EXTENDED)
        listbox.grid(row=0, column=0, columnspan=3, padx=8, pady=(8, 4), sticky="nsew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        add_file_btn = ttk.Button(frame, text="Add Files", command=lambda: self._add_files(listbox))
        add_file_btn.grid(row=1, column=0, padx=8, pady=4, sticky="ew")

        add_dir_btn = ttk.Button(frame, text="Add Folder", command=lambda: self._add_directory(listbox))
        add_dir_btn.grid(row=1, column=1, padx=8, pady=4, sticky="ew")

        remove_btn = ttk.Button(frame, text="Remove Selected", command=lambda: self._remove_from_list(listbox))
        remove_btn.grid(row=1, column=2, padx=8, pady=4, sticky="ew")

        return listbox

    def _build_controls(self) -> None:
        options_frame = ttk.LabelFrame(self.root, text="Options")
        options_frame.grid(row=1, column=0, padx=12, pady=8, sticky="ew")

        ttk.Checkbutton(
            options_frame,
            text="Include hidden files",
            variable=self.include_hidden,
        ).grid(row=0, column=0, padx=8, pady=6, sticky="w")

        output_label = ttk.Label(options_frame, text="Output path (file or directory):")
        output_label.grid(row=1, column=0, padx=8, pady=(6, 2), sticky="w")

        output_entry = ttk.Entry(options_frame, textvariable=self.output_path)
        output_entry.grid(row=2, column=0, padx=8, pady=(0, 6), sticky="ew")
        options_frame.grid_columnconfigure(0, weight=1)

        buttons_frame = ttk.Frame(options_frame)
        buttons_frame.grid(row=2, column=1, padx=8, pady=(0, 6))

        ttk.Button(buttons_frame, text="Save As…", command=self._select_output_file).grid(row=0, column=0, padx=(0, 4))
        ttk.Button(buttons_frame, text="Choose Folder…", command=self._select_output_directory).grid(row=0, column=1, padx=(0, 4))
        ttk.Button(buttons_frame, text="Clear", command=lambda: self.output_path.set("")).grid(row=0, column=2)

        self.create_button = ttk.Button(self.root, text="Create Archive", command=self._on_create_clicked)
        self.create_button.grid(row=4, column=0, padx=12, pady=(4, 12), sticky="e")

    def _build_status_area(self) -> None:
        frame = ttk.LabelFrame(self.root, text="Status")
        frame.grid(row=3, column=0, padx=12, pady=8, sticky="nsew")
        self.root.grid_rowconfigure(3, weight=1)

        self.status_text = tk.Text(frame, height=8, wrap="word", state="disabled")
        self.status_text.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.status_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=8)
        self.status_text["yscrollcommand"] = scrollbar.set

        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

    # --------------------------------------------------------------- actions --
    def _add_files(self, listbox: tk.Listbox) -> None:
        selections = filedialog.askopenfilenames(title="Select files")
        if not selections:
            return
        self._target_list(listbox).add(selections)

    def _add_directory(self, listbox: tk.Listbox) -> None:
        selection = filedialog.askdirectory(title="Select folder")
        if not selection:
            return
        self._target_list(listbox).add([selection])

    def _remove_from_list(self, listbox: tk.Listbox) -> None:
        self._target_list(listbox).remove_selected()

    def _target_list(self, listbox: tk.Listbox) -> SelectionList:
        if listbox is self.sources_list.listbox:
            return self.sources_list
        return self.destinations_list

    def _select_output_file(self) -> None:
        filename = filedialog.asksaveasfilename(
            title="Save archive as",
            defaultextension=".zip",
            filetypes=[("ZIP archives", "*.zip"), ("All files", "*.*")],
        )
        if filename:
            self.output_path.set(filename)

    def _select_output_directory(self) -> None:
        directory = filedialog.askdirectory(title="Select output directory")
        if directory:
            self.output_path.set(directory)

    # --------------------------------------------------------------- status --
    def _log(self, message: str) -> None:
        self.status_text.configure(state="normal")
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.configure(state="disabled")

    def _clear_status(self) -> None:
        self.status_text.configure(state="normal")
        self.status_text.delete("1.0", tk.END)
        self.status_text.configure(state="disabled")

    # ----------------------------------------------------------------- jobs --
    def _on_create_clicked(self) -> None:
        if not self.sources_list.values:
            messagebox.showerror("Missing sources", "Please add at least one file or folder to archive.")
            return

        threading.Thread(target=self._create_archive_job, daemon=True).start()

    def _create_archive_job(self) -> None:
        self._set_controls_state(tk.DISABLED)
        self._clear_status()
        try:
            archive = create_archive(
                [Path(src) for src in self.sources_list.values],
                output=Path(self.output_path.get()) if self.output_path.get() else None,
                include_hidden=self.include_hidden.get(),
            )
            self._log(f"Archive created at: {archive}")

            if self.destinations_list.values:
                results = copy_to_locations(archive, [Path(dest) for dest in self.destinations_list.values])
                for directory, copied_file in results:
                    self._log(f"Copied archive to {copied_file} (destination: {directory})")
            messagebox.showinfo("Success", "Archive created successfully.")
        except Exception as exc:  # pragma: no cover - surfaced via GUI
            messagebox.showerror("Error", str(exc))
            self._log(f"Error: {exc}")
        finally:
            self._set_controls_state(tk.NORMAL)

    def _set_controls_state(self, state: str) -> None:
        self._set_state_recursive(self.root, state)

    def _set_state_recursive(self, widget: tk.Widget, state: str) -> None:
        interactive = (ttk.Button, ttk.Checkbutton, ttk.Entry, tk.Listbox)
        if isinstance(widget, interactive):
            try:
                widget.configure(state=state)
            except tk.TclError:
                pass
        for child in widget.winfo_children():
            self._set_state_recursive(child, state)


def main() -> None:
    try:
        root = tk.Tk()
    except tk.TclError as exc:  # pragma: no cover - exercised via unit test with mock
        message = "Unable to initialize the FileZipper GUI. Ensure a graphical display is available."
        raise SystemExit(message) from exc

    FileZipperApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
