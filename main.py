import tkinter as tk
from tkinter import messagebox
import sqlite3
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import secrets  # More secure than random
from datetime import datetime
import re
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='app.log'
)

# Configuration class for UI constants
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

# Custom exceptions
class AppError(Exception):
    """Base exception class for the application"""
    pass

class DatabaseError(AppError):
    """Database related errors"""
    pass

class ValidationError(AppError):
    """Data validation errors"""
    pass

# Database manager class
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
                name TEXT,
                email TEXT,
                date TEXT,
                type TEXT,
                completion TEXT,
                deadline TEXT,
                service TEXT)''')
            
            conn.commit()

# Data validator class
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

class DatabaseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("@cervusTable")
        self.root.geometry("1000x600")
        self.config = UIConfig()
        self.root.configure(bg=self.config.BACKGROUND_COLOR)
        
        # Initialize database manager
        self.db_manager = DatabaseManager()
        
        # Initialize components
        self.init_database()
        self.init_ui()
        self.load_data()
        
        # Setup closing protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def generate_client_id(self) -> str:
        """Generate a secure random client ID"""
        return f"AUT-{secrets.randbelow(9000) + 1000}"
    
    def generate_budget_id(self) -> str:
        """Generate a secure random budget ID"""
        return f"ART-{secrets.randbelow(9000) + 1000}"

    def init_database(self):
        try:
            self.db_manager.init_database()
        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {e}")
            messagebox.showerror("Database Error", f"Failed to initialize database: {e}")

    def init_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create frames
        self.client_frame = ttk.Frame(self.notebook)
        self.budget_frame = ttk.Frame(self.notebook)
        self.contract_services_frame = ttk.Frame(self.notebook)
        self.service_registration_frame = ttk.Frame(self.notebook)

        # Add frames to notebook
        self.notebook.add(self.client_frame, text="Cadastro de Clientes")
        self.notebook.add(self.budget_frame, text="Orçamento")
        self.notebook.add(self.contract_services_frame, text="Serviços Contratados")
        self.notebook.add(self.service_registration_frame, text="Cadastro de Serviços")

        # Initialize UI components
        self.init_client_ui()
        self.init_budget_ui()
        self.init_contract_services_ui()
        self.init_service_registration_ui()

    def init_client_ui(self):
        # Title
        title_label = ttk.Label(
            self.client_frame, 
            text="Cadastro de Clientes", 
            font=("Helvetica", 16, "bold"), 
            foreground=self.config.TEXT_COLOR
        )
        title_label.pack(pady=(20, 10))

        # Search bar
        search_frame = ttk.Frame(self.client_frame)
        search_frame.pack(fill=tk.X, pady=10)

        search_button = ttk.Button(
            search_frame,
            text="Buscar",
            command=self.filter_data,
            bootstyle="info-outline"
        )
        search_button.pack(side=tk.RIGHT, padx=5)

        self.search_entry = ttk.Entry(search_frame, width=20)
        self.search_entry.pack(side=tk.RIGHT, padx=5)
        self.search_entry.bind("<KeyRelease>", self.filter_data)

        #Barra de Pesquisa
        search_label = ttk.Label(
            search_frame, 
            text="Pesquisar:", 
            font=("Helvetica", 10, "bold"), 
            foreground=self.config.TEXT_COLOR
        )
        search_label.pack(side=tk.RIGHT, padx=5)

        # Treeview
        self.tree = ttk.Treeview(
            self.client_frame,
            columns=("ID", "Nome", "Email", "Telefone", "Observação", "Data de Cadastro"),
            show="headings"
        )
        
        # Configure headings
        client_headings = {
            "ID": {"width": 100, "anchor": "center"},
            "Nome": {"width": 120, "anchor": "w"},
            "Email": {"width": 120, "anchor": "w"},
            "Telefone": {"width": 120, "anchor": "center"},
            "Observação": {"width": 120, "anchor": "w"},
            "Data de Cadastro": {"width": 120, "anchor": "center"}
        }

        for col, props in client_headings.items():
            self.tree.heading(col, text=col, anchor=props["anchor"])
            self.tree.column(col, width=props["width"], anchor=props["anchor"])

        # Scrollbar
        client_scrollbar = ttk.Scrollbar(self.client_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=client_scrollbar.set)
        client_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Buttons frame
        client_button_frame = ttk.Frame(self.client_frame)
        client_button_frame.pack(fill=tk.X, pady=10)

        # Buttons
        client_buttons = [
            ("Adicionar", "success-outline", self.open_add_client_dialog),
            ("Editar", "warning-outline", self.open_edit_client_dialog),
            ("Excluir", "danger-outline", self.delete_client_record),
            ("Recarregar", "info-outline", self.load_data)
        ]

        for text, style, command in client_buttons:
            btn = ttk.Button(
                client_button_frame,
                text=text,
                command=command,
                bootstyle=style
            )
            btn.pack(side=tk.LEFT, padx=5, pady=2)

    def init_budget_ui(self):
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
            columns=("ID", "Nome", "Email", "Data", "Tipo", "Previsão de Conclusão", "Prazo", "Serviço"),
            show="headings"
        )
        
        # Configure headings
        budget_headings = {
            "ID": {"width": 100, "anchor": "center"},
            "Nome": {"width": 150, "anchor": "w"},
            "Email": {"width": 150, "anchor": "w"},
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

    def init_contract_services_ui(self):
        # Title
        title_label = ttk.Label(
            self.contract_services_frame, 
            text="Serviços Contratados", 
            font=("Helvetica", 16, "bold"), 
            foreground=self.config.TEXT_COLOR
        )
        title_label.pack(pady=(20, 10))

    def init_service_registration_ui(self):
        # Title
        title_label = ttk.Label(
            self.service_registration_frame, 
            text="Cadastro de Serviços", 
            font=("Helvetica", 16, "bold"), 
            foreground=self.config.TEXT_COLOR
        )
        title_label.pack(pady=(20, 10))

    def open_edit_client_dialog(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Aviso", "Selecione um cliente para editar.")
            return

        item = self.tree.item(selected_item)
        client_id = item['values'][0]

        dialog = self.create_dialog(self.root, "Editar Cliente - Passo 1")

        # Create entry fields
        entries = {
            "Nome:": item['values'][1],
            "Email:": item['values'][2],
            "Telefone:": item['values'][3]
        }

        entry_widgets = {}
        for label_text, value in entries.items():
            ttk.Label(
                dialog,
                text=label_text,
                font=("Helvetica", 10, "bold"),
                foreground=self.config.TEXT_COLOR2,
                background=self.config.BACKGROUND_COLOR
            ).pack(pady=5)
            
            entry = ttk.Entry(dialog)
            entry.pack(pady=5)
            entry.configure(background=self.config.ENTRY_BACKGROUND)
            entry.insert(0, value)
            entry_widgets[label_text] = entry

            if label_text == "Telefone:":
                entry.bind("<KeyRelease>", self.format_phone_entry)

        def next_step():
            name = entry_widgets["Nome:"].get()
            email = entry_widgets["Email:"].get()
            phone = entry_widgets["Telefone:"].get()

            if name == "Digite o nome" or not name:
                messagebox.showwarning("Aviso", "O campo nome é obrigatório!")
                entry_widgets["Nome:"].config(bootstyle="danger")
                return

            if email != "Digite o email" and not DataValidator.validate_email(email):
                messagebox.showwarning("Aviso", "Email inválido!")
                entry_widgets["Email:"].config(bootstyle="danger")
                return

            dialog.destroy()
            self.open_edit_client_observation_dialog(client_id, name, email, phone)

        # Button frame
        button_frame = ttk.Frame(dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)

        ttk.Button(
            button_frame,
            text="Próximo",
            command=next_step,
            bootstyle="success-outline"
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            button_frame,
            text="Cancelar",
            command=dialog.destroy,
            bootstyle="danger-outline"
        ).pack(side=tk.RIGHT, padx=5)

    def delete_client_record(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Aviso", "Selecione um cliente para excluir.")
            return

        item = self.tree.item(selected_item)
        client_id = item['values'][0]

        confirm = messagebox.askyesno("Confirmação", "Tem certeza que deseja excluir este cliente?")
        if confirm:
            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM clients WHERE client_id=?", (client_id,))
                    conn.commit()
                self.load_data()
                messagebox.showinfo("Sucesso", "Cliente excluído com sucesso!")
            except Exception as e:
                logging.error(f"Error deleting client: {e}")
                messagebox.showerror("Erro", f"Erro ao excluir cliente: {e}")

    def open_add_client_dialog(self):
        dialog = self.create_dialog(self.root, "Adicionar Cliente")

        # Create entry fields
        entries = {
            "Nome:": "Digite o nome",
            "Email:": "Digite o email",
            "Telefone:": "(XX) X XXXX-XXXX"
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
            
            entry = ttk.Entry(dialog)
            entry.pack(pady=5)
            entry.configure(background=self.config.ENTRY_BACKGROUND)
            self.add_placeholder(entry, placeholder)
            entry_widgets[label_text] = entry

            if label_text == "Telefone:":
                entry.bind("<KeyRelease>", self.format_phone_entry)

        def next_step():
            name = entry_widgets["Nome:"].get()
            email = entry_widgets["Email:"].get()
            phone = entry_widgets["Telefone:"].get()

            if name == "Digite o nome" or not name:
                messagebox.showwarning("Aviso", "O campo nome é obrigatório!")
                entry_widgets["Nome:"].config(bootstyle="danger")
                return

            if email != "Digite o email" and not DataValidator.validate_email(email):
                messagebox.showwarning("Aviso", "Email inválido!")
                entry_widgets["Email:"].config(bootstyle="danger")
                return

            dialog.destroy()
            self.open_add_client_observation_dialog(name, email, phone)

        # Button frame
        button_frame = ttk.Frame(dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)

        ttk.Button(
            button_frame,
            text="Próximo",
            command=next_step,
            bootstyle="success-outline"
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            button_frame,
            text="Cancelar",
            command=dialog.destroy,
            bootstyle="danger-outline"
        ).pack(side=tk.RIGHT, padx=5)

    def open_add_client_observation_dialog(self, name, email, phone):
        dialog = self.create_dialog(self.root, "Adicionar Cliente - Passo 2")

        # Create entry field for observation
        ttk.Label(
            dialog,
            text="Observação:",
            font=("Helvetica", 10, "bold"),
            foreground=self.config.TEXT_COLOR2,
            background=self.config.BACKGROUND_COLOR
        ).pack(pady=5)
    
        observation_text = tk.Text(dialog, height=10, width=40)  # Define the size of the Text widget
        observation_text.pack(pady=5)
        observation_text.configure(bg=self.config.ENTRY_BACKGROUND, fg=self.config.TEXT_COLOR2, insertbackground=self.config.TEXT_COLOR2)

        def save_client():
            observation = observation_text.get("1.0", tk.END).strip()  # Get the text from the Text widget
            client_id = self.generate_client_id()
            date_added = datetime.now().strftime("%d/%m/%Y")

            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO clients (client_id, name, email, phone, observation, date_added)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (client_id, name, email, phone, observation, date_added))
                
                    conn.commit()
                    self.load_data()
                    messagebox.showinfo("Sucesso", "Cliente adicionado com sucesso!")
                    dialog.destroy()
            except Exception as e:
                logging.error(f"Error saving client: {e}")
                messagebox.showerror("Erro", f"Erro ao salvar cliente: {e}")

        # Button frame
        button_frame = ttk.Frame(dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)

        ttk.Button(
            button_frame,
            text="Salvar",
            command=save_client,
            bootstyle="success-outline"
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            button_frame,
            text="Cancelar",
            command=dialog.destroy,
            bootstyle="danger-outline"
        ).pack(side=tk.RIGHT, padx=5)

    def open_edit_client_observation_dialog(self, client_id, name, email, phone):
        dialog = self.create_dialog(self.root, "Editar Cliente - Passo 2")

        # Create entry field for observation
        ttk.Label(
            dialog,
            text="Observação:",
            font=("Helvetica", 10, "bold"),
            foreground=self.config.TEXT_COLOR2,
            background=self.config.BACKGROUND_COLOR
        ).pack(pady=5)
    
        observation_text = tk.Text(dialog, height=10, width=40)  # Define the size of the Text widget
        observation_text.pack(pady=5)
        observation_text.configure(bg=self.config.ENTRY_BACKGROUND, fg=self.config.TEXT_COLOR2, insertbackground=self.config.TEXT_COLOR2)

        def save_client():
            observation = observation_text.get("1.0", tk.END).strip()  # Get the text from the Text widget

            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE clients
                        SET name=?, email=?, phone=?, observation=?
                        WHERE client_id=?
                    """, (name, email, phone, observation, client_id))
                
                    conn.commit()
                    self.load_data()
                    messagebox.showinfo("Sucesso", "Cliente atualizado com sucesso!")
                    dialog.destroy()
            except Exception as e:
                logging.error(f"Error updating client: {e}")
                messagebox.showerror("Erro", f"Erro ao atualizar cliente: {e}")

        # Button frame
        button_frame = ttk.Frame(dialog)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)

        ttk.Button(
            button_frame,
            text="Salvar",
            command=save_client,
            bootstyle="success-outline"
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            button_frame,
            text="Cancelar",
            command=dialog.destroy,
            bootstyle="danger-outline"
        ).pack(side=tk.RIGHT, padx=5)

    def format_phone_entry(self, event):
        """Format phone entry to (XX) X XXXX-XXXX"""
        entry = event.widget
        phone = re.sub(r'\D', '', entry.get())
        formatted_phone = ""

        if len(phone) > 0:
            formatted_phone += "(" + phone[:2]
        if len(phone) > 2:
            formatted_phone += ") " + phone[2:3]
        if len(phone) > 3:
            formatted_phone += " " + phone[3:7]
        if len(phone) > 7:
            formatted_phone += "-" + phone[7:11]

        entry.delete(0, tk.END)
        entry.insert(0, formatted_phone)

    def open_add_budget_dialog(self):
        dialog = self.create_dialog(self.root, "Adicionar Orçamento")

        # Create entry fields
        entries = {
            "Nome:": "Digite o nome",
            "Email:": "Digite o email",
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
            
            entry = ttk.Entry(dialog)
            entry.pack(pady=5)
            entry.configure(background=self.config.ENTRY_BACKGROUND)
            self.add_placeholder(entry, placeholder)
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

            budget_id = self.generate_budget_id()
            date_added = datetime.now().strftime("%d/%m/%Y")

            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO budgets (budget_id, name, email, date, type, completion, deadline, service)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (budget_id, name, email, date_added, budget_type, completion, deadline, service))
                    
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
                cursor.execute("SELECT budget_id, name, email, date, type, completion, deadline, service FROM budgets")
                for row in cursor.fetchall():
                    self.budget_tree.insert("", tk.END, values=row)
        except Exception as e:
            logging.error(f"Error loading budget data: {e}")
            messagebox.showerror("Erro", f"Erro ao carregar dados de orçamento: {e}")
    
    def filter_data(self, event=None):
        """Filter data in treeview based on search entry"""
        search_term = self.search_entry.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT client_id, name, email, phone, observation, date_added FROM clients")
                for row in cursor.fetchall():
                    if (search_term in row[0].lower() or
                        search_term in row[1].lower() or
                        search_term in row[2].lower() or
                        search_term in row[3].lower() or
                        search_term in row[4].lower() or
                        search_term in row[5].lower()):
                        self.tree.insert("", tk.END, values=row)
        except Exception as e:
            logging.error(f"Error filtering data: {e}")
            messagebox.showerror("Erro", f"Erro ao filtrar dados: {e}")

    def on_close(self):
        """Handle application closing"""
        if messagebox.askokcancel("Sair", "Deseja realmente sair?"):
            self.root.destroy()

    @staticmethod
    def create_dialog(parent: tk.Tk, title: str, geometry: str = "400x350") -> tk.Toplevel:
        """Create a standard dialog window"""
        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.geometry(geometry)
        dialog.configure(bg=UIConfig.BACKGROUND_COLOR)
        return dialog

    def add_placeholder(self, entry: ttk.Entry, placeholder: str) -> None:
        """Add placeholder text to entry widget"""
        entry.insert(0, placeholder)
        entry.config(foreground=self.config.PLACEHOLDER_COLOR)
        
        def on_focus_in(event):
            if entry.get() == placeholder:
                entry.delete(0, tk.END)
                entry.config(foreground=self.config.TEXT_COLOR)
        
        def on_focus_out(event):
            if not entry.get():
                entry.insert(0, placeholder)
                entry.config(foreground=self.config.PLACEHOLDER_COLOR)

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

    def load_data(self):
        """Load client data from database into treeview"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT client_id, name, email, phone, observation, date_added FROM clients")
                for row in cursor.fetchall():
                    self.tree.insert("", tk.END, values=row)
        except Exception as e:
            logging.error(f"Error loading client data: {e}")
            messagebox.showerror("Erro", f"Erro ao carregar dados de clientes: {e}")

    def open_edit_budget_dialog(self):
        selected_item = self.budget_tree.selection()
        if not selected_item:
            messagebox.showwarning("Aviso", "Selecione um orçamento para editar.")
            return

        item = self.budget_tree.item(selected_item)
        budget_id = item['values'][0]

        dialog = self.create_dialog(self.root, "Editar Orçamento")

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

def main():
    """Main application entry point"""
    try:
        root = tk.Tk()
        style = ttk.Style(theme="darkly")  # You can change the theme here
        app = DatabaseApp(root)
        root.mainloop()
    except Exception as e:
        logging.critical(f"Application failed to start: {e}")
        messagebox.showerror("Critical Error", f"Application failed to start: {e}")

if __name__ == "__main__":
    main()