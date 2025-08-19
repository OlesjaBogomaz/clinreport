#! /usr/bin/env python3


import tkinter as tk
from tkinter import ttk, filedialog, messagebox, CENTER
import os
import sys
import sqlite3
import traceback
import json
import shutil
from pathlib import Path
import pandas as pd

from utils import load_config, get_ru_annotations
from clinreport import ClinReport
from database import Database


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
        self.config = load_config(self.config_path)

        self.clinreport = None
        self.ru_annotations = self.setup_ru_annotations()
        self.setup_database()

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


    def setup_database(self):
        self.database = None
        try:
            self.database = Database(db_creds=self.config)
        except Exception as e:
            messagebox.showwarning("Проблема с подключением к БД", f"{traceback.format_exc()}")


    def setup_ru_annotations(self):
        try:
            return get_ru_annotations()
        except Exception as e:
            messagebox.showwarning('Летмиспикфромахарт', f"Проблема с получением аннотаций на русском: {repr(e)}")
        

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
            clinician = self.config.get('clinician', 'Не указан') 
            
            self.clinreport = ClinReport(filepath, clinician=clinician, ru_annotations=self.ru_annotations)
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
        self.database = self.master.database
        self.clinreport = self.master.clinreport
        self.sample = sample
        self.title(f"Образец {self.sample}")
        self.geometry("850x850")
        self.style = ttk.Style(self)
        self.style.configure('Treeview', rowheight=40)
        self.auto_upload = self.master.config.get('auto_upload')

        self.save_button = tk.Button(self, text="Сохранить как ...", command=self.save_docx)
        self.save_button.pack(pady=5)

        self.upload_button = tk.Button(self, text="Выгрузить в базу", command=self.insert_to_db)
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
        for note, columns in zip(['1', '2', '3', '7', '8'], [self.clinreport.SNV_table_header + ("Ручные критерии",)]*4+[self.clinreport.C_table_header + ("Ручные критерии",)]):
            note_variants_data = self.clinreport.filter_variants(sample_variants_data, by_note=note)
            variants_rows = [[row[col] for col in columns] for row in note_variants_data]
            self.variants_tableviews[note] = self.pack_tableview(columns, variants_rows, with_buttons=True)

    def pack_tableview(self, columns: list | tuple, rows: list, with_buttons: bool = False
    ) -> ttk.Treeview:
       
        # Создаем фрейм для таблицы и кнопок
        frame = ttk.Frame(self.scrollable_frame)
        frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Создаем таблицу
        tableview = Tableview(frame, columns=columns, show="headings")
        for col in columns:
            tableview.heading(col, text=col)
            tableview.column(col, width=100)
        
        # Заполняем таблицу данными
        for i, row in enumerate(rows):
            tableview.insert("", tk.END, values=row, tags=(i,))
        
        tableview.config(height=len(rows)+3 if len(rows) else 0)
        tableview.pack(side="left", fill="both", expand=True)
        
        # Добавляем кнопки если нужно
        if with_buttons:
            # Создаем фрейм для кнопок
            button_frame = ttk.Frame(frame)
            button_frame.pack(side="right", fill="y")

            ind = columns.index('Изменение ДНК (HG38) (Изменение белка)')
            
            # Добавляем кнопки для каждой строки
            for i, row in enumerate(rows):
                btn = tk.Button(
                    button_frame,
                    text="Похожие",
                    command=lambda vd=row[ind]: self.show_similar_variants(vd),
                    width=8
                )
                btn.pack(pady=2)
        
        return tableview

    def show_similar_variants(self, variant_data):
        """Показывает похожие варианты из базы данных"""
        similar_window = tk.Toplevel(self)
        dna_change = variant_data.split('\n')[0]
        similar_window.title(f"Похожие варианты для {dna_change}")
        similar_window.geometry("800x400")
        
        
        try:
            # Получаем похожие варианты из базы данных
            similar_variants = self.master.database.get_similar_variants(dna_change)
            
            # Создаем таблицу для отображения
            columns = ['Образец', 'Патогенность', 'Клиницист', 'Дата заключения']
            tree = ttk.Treeview(similar_window, columns=columns, show="headings")
            
            for col in columns:
                tree.heading(col, text=col)
                tree.column(col, width=150)
            
            for variant in similar_variants:
                tree.insert("", tk.END, values=(
                    variant['Номер образца'],
                    variant['Патогенность'],
                    variant['Клиницист'],
                    variant['Дата заключения']
                ))
            
            tree.pack(fill="both", expand=True)
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось получить данные: {str(e)}")


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
        """Сохраняет документ и при необходимости выгружает в БД."""

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

                if self.auto_upload:
                    self.insert_to_db()
                    messagebox.showinfo("Успешно", "Документ сохранен и данные выгружены в БД")
                else:
                    messagebox.showinfo("Успешно", "Документ сохранен")
                    
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при сохранении документа: {repr(e)}")


    def insert_to_db(self) -> None:
        try:
            sample_name = str(self.sample).split(".")[0]
            if self.database.sample_data_exists(sample_name):
                answer = messagebox.askyesno(
                    "Найден дубликат образца",
                    f'Для образца "{sample_name}" есть записи в БД. Вы хотите записать еще?'
                )
                if not answer:
                    return
            sample_payload = self.clinreport.sample_data_to_payload(self.clinreport.data[self.sample])
            self.database.insert(sample_payload)
            messagebox.showinfo("Успешно", f"{len(sample_payload)} вариант(ов) успешно выгружены")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при выгрузке данных: {repr(e)}")


    def close(self) -> None:
        self.destroy()


class SettingsWindow(tk.Toplevel):
    """Окно настроек."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Настройки")
        self.geometry("420x350")  # Установите желаемый размер

        self.labels, self.entries, self.switches = {}, {}, {}
        
        for row, (key, value) in enumerate(self.master.config.items()):
            if key == 'auto_upload':
                self.auto_upload_var = tk.BooleanVar(value=value)
                self.switches['auto_upload'] = ttk.Checkbutton(
                    self,
                    text="Автоматически выгружать в БД при сохранении",
                    variable=self.auto_upload_var
                )
                self.switches['auto_upload'].grid(row=row, column=0, columnspan=2, padx=5, pady=10, sticky=tk.W)
            else:
                self.labels[key] = ttk.Label(self, text=f"{key}:")
                self.labels[key].grid(row=row, column=0, padx=5, pady=5, sticky=tk.W)
                self.entries[key] = ttk.Entry(self)
                self.entries[key].insert(0, str(value))  # Преобразуем значение в строку
                self.entries[key].grid(row=row, column=1, padx=5, pady=5, sticky=tk.EW)

        
        self.save_button = tk.Button(self, text="Сохранить", command=self.save_settings)
        self.save_button.grid(row=len(self.entries)+1, column=0, columnspan=2, padx=5, pady=10)


    def save_settings(self):
        """Сохраняет настройки в json."""
        for key, entry in self.entries.items():
            self.master.config[key] = entry.get()

        try:
            with open(self.master.config_path, 'w') as f:
                json.dump(self.master.config, f)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сохранении настроек: {repr(e)}")

class Tableview(ttk.Treeview):
    """Editable Treeview with forced dark text on light background"""
    
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._setup_table_style()
        self._text_editor = None
        self._scrollbar = None
        

    def _setup_table_style(self):
        style = ttk.Style(self)

        style.configure("Treeview",
            background="white",
            foreground="black",
            fieldbackground="white",
            borderwidth=1,
            relief="solid",
            font=('Helvetica', 10),
            selectbackground="white",  
            selectforeground="black"
            )

        style.map('Treeview', 
            background=[('selected', 'white')],  
            foreground=[('selected', 'black')]   
            )


        
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
