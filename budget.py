import tkinter as tk
from tkinter import messagebox
import sqlite3
import ttkbootstrap as ttk
from datetime import datetime
import logging
import secrets
import re
from contextlib import contextmanager
from dataclasses import dataclass
from tkinter import ttk

#Esse arquivo é responsável pela parte do ORÇAMENTO.
# Conteúdo do arquivo utils.py
@dataclass
class UIConfig:
    BACKGROUND_COLOR: str = "#FFFFFF"
    BUTTON_COLOR: str = "#4CAF50"
    BUTTON_HOVER_COLOR: str = "#45a049"
    TEXT_COLOR: str = "#FFFFFF"
    TEXT_COLOR2: str = "#000000"
    PLACEHOLDER_COLOR: str = "#A9A9A9"
    ENTRY_BACKGROUND: str = "#FFFFFF"
    ENTRY_BORDER_COLOR: str = "#CCCCCC"
    SELECTION_COLOR: str = "#4CAF50"
    SELECTION_TEXT_COLOR: str = "#FFFFFF"
    HEADER_BACKGROUND: str = "#f2f2f2"
    HEADER_TEXT_COLOR: str = "#000000"
    ERROR_COLOR: str = "#FF0000"

class DataValidator:
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

    @staticmethod
    def validate_email(email: str) -> bool:
        return bool(DataValidator.EMAIL_REGEX.match(email))

    @staticmethod
    def validate_phone(phone: str) -> bool:
        regex = r'^\(?\d{2}\)?[\s-]?\d{4,5}-?\d{4}$'
        return bool(re.match(regex, phone))

    @staticmethod
    def sanitize_input(data: str) -> str:
        return data.strip()

    @staticmethod
    def validate_input(data: str, max_length: int = 100) -> bool:
        return bool(data and len(data) <= max_length)

# Conteúdo do arquivo database.py
class DatabaseManager:
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path

    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30)
            yield conn
        finally:
            if conn:
                conn.close()

    def init_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT,
                name TEXT,
                email TEXT,
                phone TEXT,
                observation TEXT,
                date_added TEXT)''')
            
            # Check and add columns if they don't exist
            cursor.execute("PRAGMA table_info(clients)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'client_id' not in columns:
                cursor.execute("ALTER TABLE clients ADD COLUMN client_id TEXT")
            if 'date_added' not in columns:
                cursor.execute("ALTER TABLE clients ADD COLUMN date_added TEXT")
            
            # Create budgets table
            cursor.execute('''CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                budget_id TEXT,
                client_id TEXT,
                date TEXT,
                type TEXT,
                completion TEXT,
                deadline TEXT,
                service TEXT)''')
            
            # Create users table
            logging.info("Creating users table if not exists")
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT)''')
            logging.info("Users table created or already exists")
            
            conn.commit()

# Classe BudgetManager
class BudgetManager:
    def __init__(self, db_manager, config):
        self.db_manager = db_manager
        self.config = config

    def init_budget_ui(self, notebook):
        self.budget_frame = ttk.Frame(notebook)
        notebook.add(self.budget_frame, text="Orçamento")

        # Title
        title_label = ttk.Label(
            self.budget_frame, 
            text="Orçamento", 
            font=("Helvetica", 16, "bold"), 
            foreground=self.config.TEXT_COLOR
        )
        title_label.pack(pady=(20, 10))

        # Treeview
        self.budget_tree = ttk.Treeview(
            self.budget_frame,
            columns=("ID", "Nome do Cliente", "Data", "Tipo", "Previsão de Conclusão", "Prazo", "Serviço"),
            show="headings"
        )
        
        # Configure headings
        budget_headings = {
            "ID": {"width": 100, "anchor": "center"},
            "Nome do Cliente": {"width": 150, "anchor": "center"},
            "Data": {"width": 120, "anchor": "center"},
            "Tipo": {"width": 120, "anchor": "w"},
            "Previsão de Conclusão": {"width": 150, "anchor": "center"},
            "Prazo": {"width": 120, "anchor": "center"},
            "Serviço": {"width": 150, "anchor": "w"}
        }

        for col, props in budget_headings.items():
            self.budget_tree.heading(col, text=col, anchor=props["anchor"])
            self.budget_tree.column(col, width=props["width"], anchor=props["anchor"])

        # Scrollbar
        budget_scrollbar = ttk.Scrollbar(self.budget_frame, orient=tk.VERTICAL, command=self.budget_tree.yview)
        self.budget_tree.configure(yscroll=budget_scrollbar.set)
        budget_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.budget_tree.pack(fill=tk.BOTH, expand=True)

        # Buttons frame
        budget_button_frame = ttk.Frame(self.budget_frame)
        budget_button_frame.pack(fill=tk.X, pady=10)

        # Buttons
        budget_buttons = [
            ("Adicionar", "success-outline", self.open_add_budget_dialog),
            ("Editar", "warning-outline", self.open_edit_budget_dialog),
            ("Excluir", "danger-outline", self.delete_budget_record),
            ("Recarregar", "info-outline", self.load_budget_data)
        ]

        for text, style, command in budget_buttons:
            btn = ttk.Button(
                budget_button_frame,
                text=text,
                command=command,
                bootstyle=style
            )
            btn.pack(side=tk.LEFT, padx=5, pady=2)

    def open_add_budget_dialog(self, client_name=None):
        dialog = self.create_dialog(self.budget_frame, "Adicionar Orçamento")

        # Create entry fields
        entries = {
            "Nome do Cliente:": client_name if client_name else "Digite o nome do cliente",
            "Tipo:": "Selecione o tipo",
            "Previsão de Conclusão:": "Selecione a data",
            "Prazo:": "Digite o prazo",
            "Serviço:": "Selecione o serviço"
        }

        entry_widgets = {}
        for label_text, placeholder in entries.items():
            ttk.Label(
                dialog,
                text=label_text,
                font=("Helvetica", 10, "bold"),
                foreground=self.config.TEXT_COLOR2,
                background=self.config.BACKGROUND_COLOR
            ).pack(pady=5)
            
            if label_text == "Nome do Cliente:":
                entry = ttk.Combobox(dialog)
                entry.pack(pady=5)
                entry.configure(background=self.config.ENTRY_BACKGROUND)
                self.populate_client_names(entry)
                entry.bind("<KeyRelease>", lambda event: self.filter_client_names(entry))
            else:
                entry = ttk.Entry(dialog)
                entry.pack(pady=5)
                entry.configure(background=self.config.ENTRY_BACKGROUND)
                self.add_placeholder(entry, placeholder)
            
            entry_widgets[label_text] = entry

        def save_budget():
            client_name = entry_widgets["Nome do Cliente:"].get()
            budget_type = entry_widgets["Tipo:"].get()
            completion = entry_widgets["Previsão de Conclusão:"].get()
            deadline = entry_widgets["Prazo:"].get()
            service = entry_widgets["Serviço:"].get()

            if client_name == "Digite o nome do cliente" or not client_name:
                messagebox.showwarning("Aviso", "O campo Nome do Cliente é obrigatório!")
                entry_widgets["Nome do Cliente:"].config(bootstyle="danger")
                return

            budget_id = self.generate_budget_id()
            date_added = datetime.now().strftime("%d/%m/%Y")

            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO budgets (budget_id, client_id, date, type, completion, deadline, service)
                        VALUES (?, (SELECT client_id FROM clients WHERE name=?), ?, ?, ?, ?, ?)
                    """, (budget_id, client_name, date_added, budget_type, completion, deadline, service))
                    conn.commit()
                self.load_budget_data()
                messagebox.showinfo("Sucesso", "Orçamento adicionado com sucesso!")
                dialog.destroy()
            except Exception as e:
                logging.error(f"Error saving budget: {e}")
                messagebox.showerror("Erro", f"Erro ao salvar orçamento: {e}")

        # Button frame
        button_frame = ttk.Frame(dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)

        ttk.Button(
            button_frame,
            text="Salvar",
            command=save_budget,
            bootstyle="success-outline"
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            button_frame,
            text="Cancelar",
            command=dialog.destroy,
            bootstyle="danger-outline"
        ).pack(side=tk.RIGHT, padx=5)

    def populate_client_names(self, combobox):
        """Populate the combobox with client names from the database"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM clients")
                client_names = [row[0] for row in cursor.fetchall()]
                combobox['values'] = client_names
        except Exception as e:
            logging.error(f"Error loading client names: {e}")
            messagebox.showerror("Erro", f"Erro ao carregar nomes de clientes: {e}")

    def filter_client_names(self, combobox):
        """Filter the client names in the combobox based on user input"""
        user_input = combobox.get().lower()
        filtered_names = [name for name in combobox['values'] if user_input in name.lower()]
        combobox['values'] = filtered_names
        combobox.event_generate('<Down>')

    def open_edit_budget_dialog(self):
        selected_item = self.budget_tree.selection()
        if not selected_item:
            messagebox.showwarning("Aviso", "Selecione um orçamento para editar.")
            return

        item = self.budget_tree.item(selected_item)
        budget_id = item['values'][0]

        dialog = self.create_dialog(self.budget_frame, "Editar Orçamento")

        # Create entry fields
        entries = {
            "Nome:": item['values'][1],
            "Email:": item['values'][2],
            "Tipo:": item['values'][4],
            "Previsão de Conclusão:": item['values'][5],
            "Prazo:": item['values'][6],
            "Serviço:": item['values'][7]
        }

        entry_widgets = {}
        for label_text, value in entries.items():
            ttk.Label(
                dialog,
                text=label_text,
                font=("Helvetica", 10, "bold"),
                foreground=self.config.TEXT_COLOR,
                background=self.config.BACKGROUND_COLOR
            ).pack(pady=5)
            
            entry = ttk.Entry(dialog)
            entry.pack(pady=5)
            entry.configure(background=self.config.ENTRY_BACKGROUND)
            entry.insert(0, value)
            entry_widgets[label_text] = entry

        def save_budget():
            name = entry_widgets["Nome:"].get()
            email = entry_widgets["Email:"].get()
            budget_type = entry_widgets["Tipo:"].get()
            completion = entry_widgets["Previsão de Conclusão:"].get()
            deadline = entry_widgets["Prazo:"].get()
            service = entry_widgets["Serviço:"].get()

            if name == "Digite o nome" or not name:
                messagebox.showwarning("Aviso", "O campo nome é obrigatório!")
                entry_widgets["Nome:"].config(bootstyle="danger")
                return

            if email != "Digite o email" and not DataValidator.validate_email(email):
                messagebox.showwarning("Aviso", "Email inválido!")
                entry_widgets["Email:"].config(bootstyle="danger")
                return

            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE budgets
                        SET name=?, email=?, type=?, completion=?, deadline=?, service=?
                        WHERE budget_id=?
                    """, (name, email, budget_type, completion, deadline, service, budget_id))
                    
                    conn.commit()
                    self.load_budget_data()
                    messagebox.showinfo("Sucesso", "Orçamento atualizado com sucesso!")
                    dialog.destroy()
            except Exception as e:
                logging.error(f"Error updating budget: {e}")
                messagebox.showerror("Erro", f"Erro ao atualizar orçamento: {e}")

        # Button frame
        button_frame = ttk.Frame(dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)

        ttk.Button(
            button_frame,
            text="Salvar",
            command=save_budget,
            bootstyle="success-outline"
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            button_frame,
            text="Cancelar",
            command=dialog.destroy,
            bootstyle="danger-outline"
        ).pack(side=tk.RIGHT, padx=5)

    def delete_budget_record(self):
        selected_item = self.budget_tree.selection()
        if not selected_item:
            messagebox.showwarning("Aviso", "Selecione um orçamento para excluir.")
            return

        item = self.budget_tree.item(selected_item)
        budget_id = item['values'][0]

        confirm = messagebox.askyesno("Confirmação", "Tem certeza que deseja excluir este orçamento?")
        if confirm:
            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM budgets WHERE budget_id=?", (budget_id,))
                    conn.commit()
                self.load_budget_data()
                messagebox.showinfo("Sucesso", "Orçamento excluído com sucesso!")
            except Exception as e:
                logging.error(f"Error deleting budget: {e}")
                messagebox.showerror("Erro", f"Erro ao excluir orçamento: {e}")

    def load_budget_data(self):
        """Load budget data from database into treeview"""
        for item in self.budget_tree.get_children():
            self.budget_tree.delete(item)

        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT budget_id, client_id, date, type, completion, deadline, service FROM budgets")
                for row in cursor.fetchall():
                    self.budget_tree.insert("", tk.END, values=row)
        except Exception as e:
            logging.error(f"Error loading budget data: {e}")
            messagebox.showerror("Erro", f"Erro ao carregar dados de orçamento: {e}")

    @staticmethod
    def create_dialog(parent: tk.Tk, title: str, geometry: str = "400x450") -> tk.Toplevel:
        """Create a standard dialog window"""
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.geometry(geometry)
        dialog.configure(bg=UIConfig.BACKGROUND_COLOR)
        return dialog

    @staticmethod
    def add_placeholder(entry: ttk.Entry, placeholder: str) -> None:
        """Add placeholder text to entry widget"""
        entry.insert(0, placeholder)
        entry.config(foreground=UIConfig.PLACEHOLDER_COLOR)
        
        def on_focus_in(event):
            if entry.get() == placeholder:
                entry.delete(0, tk.END)
                entry.config(foreground=UIConfig.TEXT_COLOR)
        
        def on_focus_out(event):
            if not entry.get():
                entry.insert(0, placeholder)
                entry.config(foreground=UIConfig.PLACEHOLDER_COLOR)

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

    @staticmethod
    def generate_budget_id() -> str:
        """Generate a secure random budget ID"""
        return f"ART-{secrets.randbelow(9000) + 1000}"
