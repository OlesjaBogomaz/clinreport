#! /usr/bin/env python3

from tkinter import Tk, filedialog, Button, ttk, Label
from tkinter.messagebox import showerror, showwarning, showinfo
import os
import sys
import sqlite3
import traceback

from clinreport import ClinReport


def main():
    input_sqlite = filedialog.askopenfilename(title="Выберите OpenCravat SQLite файл ...", defaultextension="sqlite")
    if not input_sqlite:
        sys.exit(0)
    if not str(input_sqlite).endswith('.sqlite'):
        showwarning(title='Невалидный файл', message=input_sqlite)
        sys.exit(0)

    clinreport = ClinReport(input_sqlite)
    window = Tk()
    window.title('АвтоРепорт')
    window.geometry('600x400+300+200')
    label = Label(text="Целевой образец (дуо/трио)")
    label.pack()
    lst = ttk.Combobox(window, values=clinreport.all_samples, width=30, state='readonly')
    lst.current(0)
    lst.pack()
    # progressbar = ttk.Progressbar(orient="horizontal", mode="indeterminate")
    def btn_action():
        clinreport.target_sample = lst.get()
        try:
            reports = clinreport.generate_reports()
            for sample, doc in reports.items():
                output_fpath = filedialog.asksaveasfilename(title='Сохранить как ...', initialfile=f'Заключение ({str(sample).split(".")[0]}).docx')
                doc.save(output_fpath)
        except Exception as e:
            showerror(title=f'Произошла ошибка', message=traceback.format_exc())
        window.destroy()
    btn = Button(window, text='Сгенерировать', command=btn_action)
    btn.pack(expand=True)
    window.mainloop()


if __name__ == '__main__':
    main()