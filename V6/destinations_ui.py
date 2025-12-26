
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import sqlite3
from . import database

def open_destinations_window(root, refresh_callback=None):
    dest_win = tk.Toplevel(root)
    dest_win.title("Manage Destinations")
    dest_win.geometry("600x450")
    dest_win.configure(bg="#f7f7f7")

    # --- Input Frame ---
    input_frame = tk.LabelFrame(dest_win, text="Destination Details", bg="#f7f7f7", padx=10, pady=10)
    input_frame.pack(padx=10, pady=10, fill="x")

    # Provider
    tk.Label(input_frame, text="Provider:", bg="#f7f7f7").grid(row=0, column=0, sticky="w", pady=2)
    provider_var = tk.StringVar()
    provider_combo = ttk.Combobox(input_frame, textvariable=provider_var, values=['local', 'gdrive', 'onedrive'], state="readonly")
    provider_combo.grid(row=0, column=1, columnspan=2, sticky="ew", padx=5, pady=2)
    provider_combo.set('local')

    # Name
    tk.Label(input_frame, text="Name:", bg="#f7f7f7").grid(row=1, column=0, sticky="w", pady=2)
    dest_name_var = tk.StringVar()
    tk.Entry(input_frame, textvariable=dest_name_var, width=40).grid(row=1, column=1, columnspan=2, sticky="ew", padx=5, pady=2)

    # Location/Path
    location_label_var = tk.StringVar(value="Path:")
    tk.Label(input_frame, textvariable=location_label_var, bg="#f7f7f7").grid(row=2, column=0, sticky="w", pady=2)
    dest_path_var = tk.StringVar()
    path_entry = tk.Entry(input_frame, textvariable=dest_path_var, width=40)
    path_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
    
    browse_button = tk.Button(input_frame, text="Browse...")
    browse_button.grid(row=2, column=2, padx=5, pady=2)

    def on_provider_change(*args):
        if provider_var.get() == 'local':
            location_label_var.set("Path:")
            browse_button.config(state="normal")
            path_entry.config(state="normal")
        else:
            location_label_var.set("Root Folder:")
            browse_button.config(state="disabled")
            path_entry.config(state="normal")
    
    provider_var.trace_add("write", on_provider_change)
    
    def browse_dest_path():
        path = filedialog.askdirectory(title="Select Destination Location")
        if path:
            dest_path_var.set(path)
    browse_button.config(command=browse_dest_path)

    input_frame.grid_columnconfigure(1, weight=1)

    # --- Existing Destinations Display ---
    dest_list_frame = tk.LabelFrame(dest_win, text="Existing Destinations", bg="#f7f7f7", padx=10, pady=10)
    dest_list_frame.pack(padx=10, pady=10, fill="both", expand=True)

    dest_cols = ("name", "provider", "location")
    dest_tree = ttk.Treeview(dest_list_frame, columns=dest_cols, show="headings", height=5)
    dest_tree.heading("name", text="Name")
    dest_tree.heading("provider", text="Provider")
    dest_tree.heading("location", text="Location/Folder")
    dest_tree.column("name", width=150, anchor="w")
    dest_tree.column("provider", width=80, anchor="w")
    dest_tree.column("location", width=300, anchor="w")

    dest_vscroll = ttk.Scrollbar(dest_list_frame, orient=tk.VERTICAL, command=dest_tree.yview)
    dest_tree.configure(yscrollcommand=dest_vscroll.set)
    dest_vscroll.pack(side=tk.RIGHT, fill="y")
    dest_tree.pack(fill="both", expand=True)

    original_name_to_edit = None

    def _edit_selected_destination(tree):
        nonlocal original_name_to_edit
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showinfo("Info", "Select a destination to edit.", parent=dest_win)
            return

        item_values = tree.item(selected_item[0], "values")
        name, provider, location = item_values[0], item_values[1], item_values[2]
        
        dest_name_var.set(name)
        provider_var.set(provider)
        dest_path_var.set(location)
        original_name_to_edit = name
        on_provider_change() # Update UI based on loaded provider

    def _delete_selected_destination(tree):
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showinfo("Info", "Select a destination to delete.", parent=dest_win)
            return

        item_values = tree.item(selected_item[0], "values")
        dest_name = item_values[0]

        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the destination '{dest_name}'?", parent=dest_win):
            try:
                database.delete_destination(dest_name)
                _refresh_destinations_list(tree)
                if refresh_callback:
                    refresh_callback()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete destination: {e}", parent=dest_win)

    dest_button_frame = tk.Frame(dest_list_frame, bg="#f7f7f7")
    dest_button_frame.pack(fill="x", pady=(5,0))
    tk.Button(dest_button_frame, text="Edit Selected", command=lambda: _edit_selected_destination(dest_tree)).pack(side=tk.RIGHT, padx=(0, 5))
    tk.Button(dest_button_frame, text="Delete Selected", command=lambda: _delete_selected_destination(dest_tree)).pack(side=tk.RIGHT)

    def _refresh_destinations_list(tree):
        for i in tree.get_children():
            tree.delete(i)
        destinations = database.list_destinations()
        for dest in destinations:
            _, name, location, provider = dest
            tree.insert("", "end", values=(name, provider, location))

    _refresh_destinations_list(dest_tree)

    def _save_destination():
        nonlocal original_name_to_edit
        name = dest_name_var.get().strip()
        location = dest_path_var.get().strip()
        provider = provider_var.get()
        
        if not name or not location:
            messagebox.showerror("Error", "Name and Location/Root Folder are required.", parent=dest_win)
            return
        
        try:
            if original_name_to_edit:
                database.update_destination(original_name_to_edit, location, provider)
            else:
                database.add_destination(name, location, provider)
            
            messagebox.showinfo("Success", f"Destination '{name}' saved.", parent=dest_win)
            _refresh_destinations_list(dest_tree)
            if refresh_callback:
                refresh_callback()
            dest_name_var.set("")
            dest_path_var.set("")
            provider_var.set("local")
            original_name_to_edit = None
        except sqlite3.IntegrityError:
                messagebox.showerror("Error", "A destination with this name already exists.", parent=dest_win)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save destination: {e}", parent=dest_win)

    button_frame = tk.Frame(dest_win, bg="#f7f7f7")
    button_frame.pack(fill="x", side=tk.BOTTOM, pady=5)
    tk.Button(button_frame, text="Save / Update", command=_save_destination).pack(side=tk.RIGHT, padx=10)
    tk.Button(button_frame, text="Clear Form", command=lambda: (dest_name_var.set(""), dest_path_var.set(""), provider_var.set("local"), globals().update(original_name_to_edit=None))).pack(side=tk.RIGHT)
    tk.Button(button_frame, text="Close", command=dest_win.destroy).pack(side=tk.LEFT, padx=10)

    on_provider_change()
    dest_win.transient(root)
    dest_win.grab_set()
    root.wait_window(dest_win)
