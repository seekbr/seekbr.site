import customtkinter as ctk
import ctypes
import yt_dlp
from tkinter import filedialog, messagebox
import os
import platform
import threading
import colorsys

# Cores
def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

def lighten(hex_color, amount=0.2):
    r, g, b = hex_to_rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
    l = min(1, l + amount)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return rgb_to_hex((int(r*255), int(g*255), int(b*255)))

def darken(hex_color, amount=0.2):
    r, g, b = hex_to_rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
    l = max(0, l - amount)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return rgb_to_hex((int(r*255), int(g*255), int(b*255)))

def saturate(hex_color, amount=0.3):
    r, g, b = hex_to_rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
    s = min(1, s + amount)
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return rgb_to_hex((int(r*255), int(g*255), int(b*255)))

def gerar_tema(fundo,primaria):
    tema = "light" if sum(hex_to_rgb(fundo)) > 360 else "dark"
    c = {
        "fundo": fundo,
        "primaria": primaria,
        "hover": darken(primaria, 0.10),
        "erro": darken("#ff0000",0.10),
        "sucesso": darken("#00ff00",0.10),
    }
    if sum(hex_to_rgb(fundo)) > 380:
        c["texto"] = lighten("#000000",0.10)
        c["barra"] = darken(fundo, 0.10)
        c["destaque"] = darken(fundo, 0.20)
    else:
        c["texto"] = darken("#FFFFFF",0.10)
        c["barra"] = lighten(fundo, 0.10)
        c["destaque"] = lighten(fundo, 0.20)

    return c


TEMA = gerar_tema("#242424","#A51F1F")

app_dir = os.path.join(os.getenv('APPDATA'), "YTDownloader")
os.makedirs(app_dir, exist_ok=True)

download_path = ""
icone_path = os.path.join(os.path.dirname(__file__), "icon.ico")
config_path = os.path.join(app_dir, "config.txt")
thread = None

app = ctk.CTk(fg_color=TEMA["fundo"])
app.title("YouTube Downloader")
app.overrideredirect(True)
app.geometry("600x460")  # aumentei para dar espaço ao status
app.iconbitmap(icone_path)

hwnd = ctypes.windll.user32.GetParent(app.winfo_id())
ctypes.windll.user32.SetWindowLongW(hwnd, -20, ctypes.windll.user32.GetWindowLongW(hwnd, -20) | 0x00040000)  # WS_EX_APPWINDOW
ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW

# Frame personalizado para a "barra de título"
top_bar = ctk.CTkFrame(app, height=30, fg_color=TEMA["barra"])  # cor cinza
top_bar.pack(fill="x", side="top")

# Botão fechar
def fechar():
    if thread:
        if thread.is_alive():  # supondo que você salve a Thread de download
            if not messagebox.askyesno("Fechar", "Um download está em andamento. Tem certeza que quer fechar?"):
                return
    app.destroy()

btn_fechar = ctk.CTkButton(top_bar, text="❌", width=30, command=fechar, fg_color="#404040", hover_color="#BB2424", corner_radius=0)
btn_fechar.pack(side="right")

# Para mover a janela ao arrastar a barra
def mover_inicio(event):
    app.x = event.x
    app.y = event.y

def mover_janela(event):
    app.geometry(f"+{event.x_root - app.x}+{event.y_root - app.y}")

top_bar.bind("<Button-1>", mover_inicio)
top_bar.bind("<B1-Motion>", mover_janela)

# ------------------------ FUNÇÕES ------------------------


def salvar_pasta(path):
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(path)
    except Exception as e:
        print("Erro ao salvar config:", e)

def carregar_pasta():
    global download_path
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                path = f.read().strip()
                if os.path.exists(path):
                    download_path = path
                    pasta_label.configure(text=f"Pasta selecionada:\n{path}")
        except:
            pass

def abrir_pasta(path):
    sistema = platform.system()
    try:
        if sistema == "Windows":
            os.startfile(path)
        elif sistema == "Darwin":  # macOS
            os.system(f"open '{path}'")
        else:  # Linux
            os.system(f"xdg-open '{path}'")
    except:
        pass

def escolher_pasta():
    global download_path
    path = filedialog.askdirectory()
    if path:
        download_path = path
        pasta_label.configure(text=f"Pasta selecionada:\n{path}")
        salvar_pasta(path)  # salva para a próxima vez

def atualizar_status(tipo,texto):
    """Atualiza o label de status na thread principal"""
    if tipo == "padrão":
        cor = TEMA["texto"]
    elif tipo == "erro":
        texto = f"🚫 Erro: {texto}"
        cor = TEMA["erro"]
    elif tipo == "sucesso":
        cor = TEMA["sucesso"]
    status_label.configure(text=texto,text_color=cor)

def callback_progresso(d):
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimated')
        if not total:
            return
        baixado = d.get('downloaded_bytes', 0)
        progresso = baixado / total
        app.after(0, lambda: progressbar.set(progresso))
    elif d['status'] == 'finished':
        app.after(0, lambda: progressbar.set(1.0))

def baixar_video():
    global thread
    thread = threading.Thread(target=_baixar_video_thread)
    thread.start()

def _baixar_video_thread():
    url = url_entry.get()

    if not url:
        app.after(0, lambda: atualizar_status("erro","Insira uma URL válida do YouTube!"))
        return

    if not download_path:
        app.after(0, lambda: atualizar_status("erro","Selecione a pasta de destino!"))
        return

    # Mostrar barra
    progressbar.set(0)
    progressbar.pack(pady=5)

    args_extrator = {"youtube": {"player_client": "android"}}
    formato = "mp4" if formato_switch.get() else "mp3"

    if formato == "mp3":
        tipo = "áudio"
        opcoes = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'progress_hooks': [callback_progresso],
            'extractor_args': args_extrator
        }
    elif formato == "mp4":
        tipo = "vídeo"
        opcoes = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'progress_hooks': [callback_progresso],
            'extractor_args': args_extrator
        }

    try:
        app.after(0, lambda: atualizar_status("padrão",f"⏳ Baixando {tipo}..."))

        with yt_dlp.YoutubeDL(opcoes) as ydl:
            ydl.download([url])

        app.after(0, lambda: atualizar_status("sucesso",f"✅ {tipo.capitalize()} baixado com sucesso!"))

        # abrir pasta
        abrir_pasta(download_path)

    except Exception as e:
        app.after(0, lambda: atualizar_status("erro",f"{e}"))

    # esconder barra após terminar
    progressbar.pack_forget()

def switch_click():
    cor = [TEMA["texto"],TEMA["primaria"]]
    label_mp3.configure(font=("Arial", 14))
    label_mp4.configure(font=("Arial", 14))
    if formato_switch.get():
        label_mp4.configure(font=("Arial", 16, "bold"))
    else:
        label_mp3.configure(font=("Arial", 16, "bold"))

# ------------------------ INTERFACE ------------------------

titulo = ctk.CTkLabel(app, text="YouTube Downloader", font=("Arial", 24, "bold"), text_color=TEMA["texto"])
titulo.pack(pady=20)

url_entry = ctk.CTkEntry(app, width=500, placeholder_text="Cole a URL do vídeo aqui",fg_color=TEMA["barra"],border_color=TEMA["destaque"],text_color=TEMA["texto"])
url_entry.pack(pady=15)

# Switch MP3 / MP4
linha_switch = ctk.CTkFrame(app, fg_color="transparent")
linha_switch.pack(pady=10)

label_mp3 = ctk.CTkLabel(linha_switch, text="MP3", font=("Arial", 14), text_color=TEMA["texto"])
label_mp3.pack(side="left", padx=10)

formato_switch = ctk.CTkSwitch(
    linha_switch,
    text="",
    width=40,
    height=20,
    fg_color=TEMA["barra"],
    progress_color=TEMA["barra"],
    button_color=TEMA["texto"],
    button_hover_color=TEMA["primaria"],
    command=switch_click,
)
formato_switch.pack(side="left", padx=10)
formato_switch.select()

label_mp4 = ctk.CTkLabel(linha_switch, text="MP4", font=("Arial", 14), text_color=TEMA["texto"])
label_mp4.pack(side="left", padx=10)

switch_click()

# Barra de progresso
progressbar = ctk.CTkProgressBar(app, width=400, fg_color=TEMA["destaque"], progress_color=TEMA["primaria"])
progressbar.set(0)
progressbar.pack(pady=5)
progressbar.pack_forget()  # invisível até iniciar download

# Botão escolher pasta
btn_pasta = ctk.CTkButton(app, text="Escolher Pasta", command=escolher_pasta, fg_color=TEMA["primaria"], hover_color=TEMA["hover"])
btn_pasta.pack(pady=10)

# Label da pasta
pasta_label = ctk.CTkLabel(app, text="Nenhuma pasta selecionada.", font=("Arial", 12), text_color=TEMA["texto"])
carregar_pasta()
pasta_label.pack()

# Botão baixar
btn_baixar = ctk.CTkButton(app, text="Baixar", command=baixar_video, fg_color=TEMA["primaria"], hover_color=TEMA["hover"])
btn_baixar.pack(pady=20)

# Label de status
status_label = ctk.CTkLabel(app, text="", font=("Arial", 14), text_color=TEMA["texto"])
status_label.pack(pady=10)

app.mainloop()