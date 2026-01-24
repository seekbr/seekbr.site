import customtkinter as ctk
import hashlib

senha = ""

ctk.set_appearance_mode("dark")   # "dark", "light" ou "system"
ctk.set_default_color_theme("green")  # "blue", "green", "dark-blue"

app = ctk.CTk()
app.title("Gerador de Senhas")
app.geometry("400x300")

def gerar_senha(segredo, extra, tamanho):
    # Junta os textos
    combinado = segredo + extra.lower().strip().replace(" ","") + str(tamanho)
    
    # Converte para bytes e aplica SHA-256
    hash_resultado = hashlib.sha256(combinado.encode()).hexdigest()
    
    # Para ser mais "senha amigável", você pode reduzir o tamanho
    nova_senha = hash_resultado[:tamanho]

    return nova_senha

def botao():
    global senha
    if not entry_base.get() or not entry_site.get():
        label.configure(text="Preencha os campos anteriores para gerar sua senha!",text_color="#c20000")
        app.after(5000, lambda: label.configure(text=""))
    else:
        if not entry_num.get():
            label.configure(text="Defina um tamanho para sua senha!",text_color="#c20000")
            app.after(5000, lambda: label.configure(text=""))
        else:
            senha = gerar_senha(entry_base.get(),entry_site.get(),int(entry_num.get()))
            texto.configure(textvariable=ctk.StringVar(value=f"{senha}"),text_color="#ececec")
            label.configure(text="Senha gerada!")
            app.after(5000, lambda: label.configure(text=""))

def copiar():
    app.clipboard_clear()
    app.clipboard_append(senha)
    label.configure(text="Senha copiada!")
    app.after(5000, lambda: label.configure(text=""))

num_var = ctk.StringVar(value="20")

def limitar_valor(*args):
    valor = num_var.get()
    if not valor.isdigit():
        num_var.set(''.join(filter(str.isdigit, valor)))
        return
    i = int(valor)
    if i > 64:
        num_var.set("64")
    elif i < 1:
        num_var.set("1")

# ======================================================

titulo = ctk.CTkLabel(app, text="Gerador de Senhas", font=("Arial", 24, "bold"), text_color="#ffffff")
titulo.pack(pady=20)

frame1 = ctk.CTkFrame(app,fg_color="transparent")
frame1.pack(pady=5)

entry_base = ctk.CTkEntry(frame1, placeholder_text="Digite sua senha base",width=150)
entry_base.pack(side="left",padx=2)

entry_site = ctk.CTkEntry(frame1, placeholder_text="Digite o nome do site",width=150)
entry_site.pack(side="left",padx=2)

entry_num = ctk.CTkEntry(frame1, textvariable=num_var, width=30)
entry_num.pack(side="left",padx=2)
entry_num.bind("<FocusOut>", limitar_valor)

frame2 = ctk.CTkFrame(app,fg_color="transparent")
frame2.pack(pady=5)

button = ctk.CTkButton(frame2, text="Gerar senha", command=botao, width=75)
button.pack(side="left",padx=1)

texto = ctk.CTkEntry(frame2, state="readonly", width=200)
texto.pack(side="left",padx=1)

copy_button = ctk.CTkButton(frame2, text="Copiar", command=copiar, width=60)
copy_button.pack(side="left",padx=1)

label = ctk.CTkLabel(app, text="")
label.pack(pady=0)

warning = ctk.CTkTextbox(app,width=380,height=120,border_spacing=0,fg_color="transparent",activate_scrollbars=False,text_color="#ffd900")
warning.insert("1.0", "⚠ Atenção: Nenhuma senha gerada aqui é armazenada ou salva nos seus arquivos locais ou na nuvem!")
warning.configure(state="disabled")  # torna readonly
warning.pack(fill="x",expand=False)

app.mainloop()