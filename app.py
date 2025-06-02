#! /usr/bin/env python3


import tkinter as tk
from tkinter import ttk, filedialog, messagebox, CENTER
import yaml
import os
import sys
import sqlite3
import traceback
import json
import shutil
from pathlib import Path

from utils import load_config
from clinreport import ClinReport


class MainWindow(tk.Tk):
    """Главное окно приложения."""

    def __init__(self):
        super().__init__()
        self.title("ClinReport")
        self.geometry("400x200")  # Установите желаемый размер

        self.select_file_button = tk.Button(self, text="Выбрать файл", command=self.select_file)
        self.select_file_button.pack(pady=20)

        self.settings_button = tk.Button(self, text="Настройки", command=self.open_settings)
        self.settings_button.pack(pady=20)

        self.config_path = self.get_config_path('clinreport_config.json')
        self.config = load_config(self.config_path)

        self.clinreport = None


    def get_config_path(self, config_fname):
        """Путь к файлу настроек рядом с exe."""
        app_dir = self.get_app_dir()
        config_path = os.path.join(app_dir, config_fname)
        try:
            self.ensure_config_exists(config_path, config_fname)
        except:
            messagebox.showwarning("Проблема конфигурации", f"{traceback.format_exc()}")
        return config_path


    def get_app_dir(self):
        """Возвращает папку, где лежит исполняемый файл или скрипт."""
        if getattr(sys, 'frozen', False):
            # Запуск из PyInstaller exe
            return os.path.dirname(sys.executable)
        else:
            # Запуск из скрипта
            return os.path.dirname(os.path.abspath(__file__))


    def ensure_config_exists(self, config_path, config_fname):
        if not os.path.exists(config_path):
            # Копируем дефолтный конфиг из ресурсов
            default_config_path = self.get_default_config_path(config_fname)
            shutil.copyfile(default_config_path, config_path)


    def get_default_config_path(self, config_fname):
        """Путь к дефолтному конфигу внутри пакета PyInstaller."""
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, config_fname)


    def select_file(self):
        """Открывает диалоговое окно выбора файла."""
        filepath = filedialog.askopenfilename(filetypes=[("SQLite files", "*.sqlite"), ("All files", "*.*")])
        if filepath:
            self.open_processing_window(filepath)


    def open_settings(self):
        """Открывает окно настроек."""
        SettingsWindow(self)


    def open_processing_window(self, filepath):
        """Открывает окно выбора типа обработки."""
        ProcessingWindow(self, filepath, self.process_file)


    def process_file(self, filepath, target_sample):
        """Обрабатывает файл в зависимости от выбранного типа."""
        try:
            self.clinreport = ClinReport(filepath, clinician=self.config['Клинический биоинформатик'])
            self.clinreport.target_sample = target_sample
            self.clinreport.get_data()
            for sample in self.clinreport.all_samples:
                ConfirmationWindow(self, sample)  # Открываем окно подтверждения
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при обработке файла: {traceback.format_exc()}")


class ProcessingWindow(tk.Toplevel):
    """Окно выбора обработки."""

    def __init__(self, master, filepath, process_file_callback):
        super().__init__(master)
        self.filepath = filepath
        self.process_file_callback = process_file_callback  # Функция, которую нужно вызвать после выбора типа
        self.title(f"{Path(filepath).name}")
        self.geometry("300x150")  # Установите желаемый размер

        self.text = tk.Label(self, text="Целевой образец:")
        self.text.pack(pady=10)

        self.clinreport = ClinReport(filepath)

        self.target_sample = ttk.Combobox(self, values=self.clinreport.all_samples, width=30, state='readonly')
        self.target_sample.current(0)
        self.target_sample.pack(pady=10)

        self.confirm_button = tk.Button(self, text="Обработать", command=self.confirm_selection)
        self.confirm_button.pack(pady=10)


    def confirm_selection(self):
        """Подтверждает выбор типа обработки и вызывает callback."""
        selected_type = self.target_sample.get()
        self.process_file_callback(self.filepath, selected_type)  # Передаем имя файла и выбранный тип
        self.destroy()


class ConfirmationWindow(tk.Toplevel):
    """Окно подтверждения данных."""

    def __init__(self, master, sample: str):
        super().__init__(master)
        self.clinreport = self.master.clinreport
        self.sample = sample
        self.title(f"Образец {self.sample}")
        self.geometry("750x800")
        self.style = ttk.Style(self)
        self.style.configure('Treeview', rowheight=40)

        self.save_button = tk.Button(self, text="Сохранить как ...", command=self.save_docx)
        self.save_button.pack(pady=5)

        self.upload_button = tk.Button(self, text="Выгрузить в базу")
        self.upload_button.pack(pady=5)

        self.close_button = tk.Button(self, text="Закрыть", command=self.close)
        self.close_button.pack(pady=5)

        self.container = ttk.Frame(self)
        self.container.pack(fill='both', expand=True)

        self.canvas = tk.Canvas(self.container)
        self.canvas.pack(side='left', fill='both', expand=True)

        self.scrollbar = ttk.Scrollbar(self.container, orient='vertical', command=self.canvas.yview)
        self.scrollbar.pack(side='right', fill='y')

        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')

        self.pack_tableviews()

        self.bind_mousewheel_recursively(self.scrollable_frame)


    def bind_mousewheel_recursively(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)
        for child in widget.winfo_children():
            self.bind_mousewheel_recursively(child)


    def _on_mousewheel(self, event):
        if event.delta:
            self.canvas.yview_scroll(int(-1*(event.delta)), "units")
        else:
            pass


    def pack_tableviews(self) -> None:
        sample_data = self.clinreport.data[self.sample]
        sample_variants_data = sample_data['variants_data']

        common_columns = [
            'Номер образца',
            'Пол пациента',
            'Возраст пациента',
            'Предварительный диагноз',
            'Средняя глубина прочтения генома после секвенирования'
        ]
        common_values = [[self.clinreport.data[self.sample][col] for col in common_columns]]
        self.common_tableview = self.pack_tableview(common_columns, common_values)

        self.variants_tableviews = {}
        for note, columns in zip(['1', '2', '3', '7', '8'], [self.clinreport.SNV_table_header]*4+[self.clinreport.C_table_header]):
            note_variants_data = self.clinreport.filter_variants(sample_variants_data, by_note=note)
            variants_rows = [[row[col] for col in columns] for row in note_variants_data]
            self.variants_tableviews[note] = self.pack_tableview(columns, variants_rows)


    def pack_tableview(self, columns: list | tuple, rows: list):
        tableview = Tableview(self.scrollable_frame, columns=columns, show="headings")
        for col in columns:
            tableview.heading(col, text=col)
            tableview.column(col, width=100)
        tableview.pack(pady=10, padx=10, fill="both", expand=True)
        for row in rows:
            tableview.insert("", tk.END, values=row)
        return tableview


    def save_tableviews_changes(self) -> None:
        common_tableview_changes = self.get_tableview_changes(self.common_tableview)[0]
        self.clinreport.data[self.sample].update(common_tableview_changes)

        for note, variants_tableview in self.variants_tableviews.items():
            note_variants_tableview_changes = self.get_tableview_changes(variants_tableview)
            j = 0
            for i, sample_variant_data in enumerate(self.clinreport.data[self.sample]['variants_data']):
                if sample_variant_data['base__note'] != note:
                    continue
                self.clinreport.data[self.sample]['variants_data'][i].update(note_variants_tableview_changes[j])
                j += 1


    def get_tableview_changes(self, tableview) -> list:
        tableview_changes = []
        for item in tableview.get_children():
            values = tableview.item(item, 'values')
            tableview_changes.append(dict(zip(tableview['columns'], values)))
        return tableview_changes


    def save_docx(self) -> None:
        self.save_tableviews_changes()
        self.doc = self.clinreport.create_doc(self.sample)
        filepath = filedialog.asksaveasfilename(
            title='Сохранить как ...',
            defaultextension=".docx",
            filetypes=[("DOCX files", "*.docx")],
            initialfile=f'Заключение ({str(self.sample).split(".")[0]}).docx'
        )
        if filepath:
            try:
                self.doc.save(filepath)
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при выгрузке данных: {e}")


    def close(self) -> None:
        self.destroy()


class SettingsWindow(tk.Toplevel):
    """Окно настроек."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Настройки")
        self.geometry("300x150")  # Установите желаемый размер

        self.label = ttk.Label(self, text="Клинический биоинформатик")
        self.label.pack(pady=5)

        self.entry = ttk.Entry(self)
        self.entry.pack(pady=5)
        self.entry.insert(0, self.master.config.get("Клинический биоинформатик", "")) # Заполняем текущим значением

        self.save_button = tk.Button(self, text="Сохранить", command=self.save_settings)
        self.save_button.pack(pady=10)


    def save_settings(self):
        """Сохраняет настройки в json."""
        new_value = self.entry.get()
        self.master.config["Клинический биоинформатик"] = new_value  # Обновляем значение ключа
        try:
            with open(self.master.config_path, 'w') as f:
                json.dump(self.master.config, f)
            self.destroy()  # Закрываем окно настроек после сохранения
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сохранении настроек: {repr(e)}")


class Tableview(ttk.Treeview):
    """Editable Treeview"""

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._text_editor = None
        self._scrollbar = None
        self.bind("<Double-1>", self._on_double_click)


    def _on_double_click(self, event):
        region = self.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.identify_row(event.y)
        col_id = self.identify_column(event.x)

        if not row_id or not col_id:
            return

        x, y, width, height = self.bbox(row_id, col_id)

        col_num = int(col_id.replace("#", "")) - 1
        item_values = list(self.item(row_id, "values"))
        if col_num >= len(item_values):
            return
        cell_value = item_values[col_num]

        if self._text_editor:
            self._text_editor.destroy()
        if self._scrollbar:
            self._scrollbar.destroy()

        self._text_editor = tk.Text(self, wrap="word", height=4)
        self._text_editor.insert("1.0", cell_value)
        self._text_editor.focus_set()

        self._scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._text_editor.yview)
        self._text_editor.configure(yscrollcommand=self._scrollbar.set)

        self._text_editor.place(x=x, y=y, width=width-15, height=height*4)
        self._scrollbar.place(x=x + width - 15, y=y, width=15, height=height*4)

        self._text_editor.bind("<FocusOut>", lambda e: self._save_edit(row_id, col_num))
        self._text_editor.bind("<Control-Return>", lambda e: self._save_edit(row_id, col_num, event=e))
        self._text_editor.bind("<Shift-Return>", lambda e: self._save_edit(row_id, col_num, event=e))
        self._text_editor.bind("<Escape>", lambda e: self._cancel_edit())


    def _save_edit(self, row_id, col_num, event=None):
        if event:
            event.widget.master.focus_set()  # Чтобы убрать фокус с Text (закрыть клавиатурный ввод)
        new_text = self._text_editor.get("1.0", "end-1c")

        # Получаем текущие значения строки
        values = list(self.item(row_id, "values"))
        values[col_num] = new_text
        self.item(row_id, values=values)

        self._text_editor.destroy()
        self._scrollbar.destroy()
        self._text_editor = None
        self._scrollbar = None


    def _cancel_edit(self):
        if self._text_editor:
            self._text_editor.destroy()
            self._text_editor = None
        if self._scrollbar:
            self._scrollbar.destroy()
            self._scrollbar = None


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
