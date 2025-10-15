"""Minimal Tk window that guides users through creating a ZIP file."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .zipper import create_zip, make_copy


def _import_tk() -> tuple["tk", "ttk", Callable[..., str], Callable[..., str], Callable[[str, str], None], Callable[[str, str], None]]:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except Exception as exc:  # pragma: no cover - import guard
        raise RuntimeError("Tkinter is not available on this system") from exc

    return (
        tk,
        ttk,
        filedialog.askopenfilename,
        filedialog.askdirectory,
        messagebox.showinfo,
        messagebox.showerror,
    )


class _App:
    def __init__(
        self,
        root: "tk.Tk",
        tk_module: "tk",
        ttk: "ttk",
        ask_file: Callable[..., str],
        ask_dir: Callable[..., str],
        show_info: Callable[[str, str], None],
        show_error: Callable[[str, str], None],
    ) -> None:
        self.root = root
        self._tk = tk_module
        self._ttk = ttk
        self._ask_file = ask_file
        self._ask_dir = ask_dir
        self._show_info = show_info
        self._show_error = show_error
        self._exit_code = 0

        self.root.title("FileZipper Helper")
        self.root.resizable(False, False)

        self.source_var = self._tk.StringVar()
        self.output_var = self._tk.StringVar()
        self.copy_var = self._tk.StringVar()

        self._build_ui()

    @property
    def exit_code(self) -> int:
        return self._exit_code

    def _build_ui(self) -> None:
        padding = {"padx": 10, "pady": 5}

        main = self._ttk.Frame(self.root, padding=15)
        main.grid(row=0, column=0, sticky="nsew")

        heading = self._ttk.Label(main, text="Zip something in three quick steps:", font=("Segoe UI", 11, "bold"))
        heading.grid(row=0, column=0, columnspan=5, sticky="w", **padding)

        self._ttk.Label(main, text="1. Pick a file or folder:").grid(row=1, column=0, sticky="w", **padding)
        source_entry = self._ttk.Entry(main, textvariable=self.source_var, width=50)
        source_entry.grid(row=1, column=1, columnspan=2, sticky="we", **padding)
        self._ttk.Button(main, text="File...", command=self._choose_source_file).grid(row=1, column=3, sticky="we", **padding)
        self._ttk.Button(main, text="Folder...", command=self._choose_source_folder).grid(row=1, column=4, sticky="we", **padding)

        self._ttk.Label(main, text="2. Where should the ZIP go? (optional)").grid(row=2, column=0, sticky="w", **padding)
        output_entry = self._ttk.Entry(main, textvariable=self.output_var, width=50)
        output_entry.grid(row=2, column=1, columnspan=2, sticky="we", **padding)
        self._ttk.Button(main, text="Browse...", command=self._choose_output).grid(row=2, column=3, sticky="we", **padding)

        self._ttk.Label(main, text="3. Extra copy somewhere else? (optional)").grid(row=3, column=0, sticky="w", **padding)
        copy_entry = self._ttk.Entry(main, textvariable=self.copy_var, width=50)
        copy_entry.grid(row=3, column=1, columnspan=2, sticky="we", **padding)
        self._ttk.Button(main, text="Browse...", command=self._choose_copy).grid(row=3, column=3, sticky="we", **padding)

        buttons = self._ttk.Frame(main)
        buttons.grid(row=4, column=0, columnspan=5, sticky="e", padx=10, pady=(15, 5))

        self._ttk.Button(buttons, text="Start", command=self._start).grid(row=0, column=0, padx=(0, 10))
        self._ttk.Button(buttons, text="Close", command=self.root.destroy).grid(row=0, column=1)

    def _choose_source_file(self) -> None:
        choice = self._ask_file(title="Select a file to zip")
        if choice:
            self.source_var.set(choice)

    def _choose_source_folder(self) -> None:
        choice = self._ask_dir(title="Select a folder to zip")
        if choice:
            self.source_var.set(choice)

    def _choose_output(self) -> None:
        choice = self._ask_dir(title="Pick where the ZIP should be saved")
        if choice:
            self.output_var.set(choice)

    def _choose_copy(self) -> None:
        choice = self._ask_dir(title="Pick where the extra copy should go")
        if choice:
            self.copy_var.set(choice)

    def _start(self) -> None:
        source_text = self.source_var.get().strip()
        if not source_text:
            self._show_error("FileZipper", "Please pick something to zip first.")
            return

        output_text = self.output_var.get().strip()
        copy_text = self.copy_var.get().strip()

        output_path = Path(output_text) if output_text else None

        try:
            archive = create_zip(Path(source_text), output_path)
        except FileNotFoundError:
            self._show_error("FileZipper", "We couldn't find that file or folder. Double-check and try again.")
            return
        except Exception as exc:  # pragma: no cover - defensive guard
            self._show_error("FileZipper", f"Something went wrong while building the ZIP: {exc}")
            return

        copy_message = ""
        if copy_text:
            try:
                copied = make_copy(archive, Path(copy_text))
            except Exception as exc:  # pragma: no cover - defensive guard
                self._show_error("FileZipper", f"We created the ZIP but couldn't copy it: {exc}")
                return
            copy_message = f"\nA backup copy was saved to:\n{copied}"

        self._show_info("FileZipper", f"All done! Your ZIP lives at:\n{archive}{copy_message}")


def launch() -> int:
    tk, ttk, ask_file, ask_dir, show_info, show_error = _import_tk()

    try:
        root = tk.Tk()
    except Exception as exc:  # pragma: no cover - defensive guard
        raise RuntimeError("Tkinter could not start a window") from exc
    app = _App(root, tk, ttk, ask_file, ask_dir, show_info, show_error)
    root.mainloop()
    return app.exit_code


__all__ = ["launch"]
