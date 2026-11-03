import os
import tkinter as tk
from tkinter import messagebox, ttk
import webbrowser
from desktop.runtime import create_administrator, has_administrator, DEMO_PASSWORD


class ControlWindow:
    def __init__(self, url, folder, bundle, factory, hidden=False):
        self.url, self.folder, self.bundle, self.factory = url, folder, bundle, factory
        self.root = tk.Tk()
        self.root.title("Chronos 1.0 - Demonstração local")
        self.root.geometry("620x440"); self.root.resizable(False, False)
        self.root.configure(background="#101f2a")
        self.root.iconbitmap(str(bundle / "desktop/chronos.ico"))
        style = ttk.Style(self.root); style.theme_use("clam")
        style.configure("TButton", padding=9, font=("Segoe UI", 10))
        frame = tk.Frame(self.root, bg="#101f2a", padx=26, pady=20); frame.pack(fill="both", expand=True)
        tk.Label(frame,text="Chronos 1.0",font=("Segoe UI",24,"bold"),fg="#e9b98c",bg="#101f2a").pack(anchor="w")
        tk.Label(frame,text="Gestão Inteligente de Jornadas e Escalas",font=("Segoe UI",11),fg="#f0eee8",bg="#101f2a").pack(anchor="w",pady=(0,15))
        tk.Label(frame,text="Pronto para usar. Mantenha esta janela aberta.",fg="#b0bfc8",bg="#101f2a",font=("Segoe UI",10)).pack(anchor="w")
        tk.Label(frame,text=url,fg="#e9b98c",bg="#101f2a",font=("Segoe UI",11,"bold")).pack(anchor="w",pady=(6,12))
        tk.Label(frame,text="Consulta: organização horizonte | usuário demo\nSenha demonstrativa: "+DEMO_PASSWORD,justify="left",fg="#f0eee8",bg="#101f2a",font=("Segoe UI",10)).pack(anchor="w")
        buttons=tk.Frame(frame,bg="#101f2a");buttons.pack(fill="x",pady=(18,8))
        ttk.Button(buttons,text="Abrir Chronos",command=lambda:webbrowser.open(url)).pack(side="left",padx=(0,8))
        self.admin_button=ttk.Button(buttons,text="Criar administrador local",command=self.administrator)
        self.admin_button.pack(side="left")
        if has_administrator(factory):self.admin_button.state(["disabled"])
        second=tk.Frame(frame,bg="#101f2a");second.pack(fill="x",pady=5)
        ttk.Button(second,text="Manual de uso",command=self.manual).pack(side="left",padx=(0,8))
        ttk.Button(second,text="Pasta de dados",command=lambda:os.startfile(str(folder))).pack(side="left",padx=(0,8))
        ttk.Button(second,text="Encerrar",command=self.root.destroy).pack(side="left")
        tk.Label(frame,text="Para editar e simular, crie seu próprio administrador local.\nDados fictícios; n8n e agendamento automático desativados.",justify="left",fg="#b0bfc8",bg="#101f2a",font=("Segoe UI",9)).pack(anchor="w",pady=(12,0))
        self.root.protocol("WM_DELETE_WINDOW",self.root.destroy)
        if hidden:self.root.withdraw()

    def manual(self):
        page = self.bundle / "help/chronos-manual.html"
        if not page.is_file():
            page = self.bundle.parent / "portfolio/chronos-manual.html"
        webbrowser.open(page.as_uri())

    def administrator(self):
        dialog=tk.Toplevel(self.root);dialog.title("Criar seu administrador local");dialog.geometry("450x290");dialog.resizable(False,False);dialog.transient(self.root);dialog.grab_set()
        values=[]
        for i,label in enumerate(("Usuário ou e-mail","Senha (12 a 128 caracteres)","Confirme a senha")):
            ttk.Label(dialog,text=label).pack(anchor="w",padx=22,pady=(12,0))
            value=ttk.Entry(dialog,show="*" if i else "",width=48);value.pack(padx=22,pady=4);values.append(value)
        def save():
            username,password,confirm=(v.get() for v in values)
            if password!=confirm:
                messagebox.showerror("Confira os campos","As senhas não coincidem.",parent=dialog);return
            try:
                name=create_administrator(self.factory,username,password)
            except ValueError as error:
                messagebox.showerror("Não foi possível criar",str(error),parent=dialog);return
            except Exception:
                messagebox.showerror("Não foi possível criar","Confira a pasta de dados e o log do Chronos.",parent=dialog);return
            self.admin_button.state(["disabled"]);dialog.destroy()
            messagebox.showinfo("Administrador criado","Entre no Chronos com organização horizonte e usuário "+name+". A senha foi armazenada como hash somente nesta instalação.",parent=self.root)
        ttk.Button(dialog,text="Criar administrador",command=save).pack(pady=14)
        values[0].focus_set()

    def run(self):self.root.mainloop()
