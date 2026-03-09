import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import requests
import json
import matplotlib
import re
import sys

# Matplotlib backend ayarı
matplotlib.use('TkAgg')

# --- KRİTİK AYARLAR ---
API_KEY = "AIzaSyCzh_IvFYXIQQaWvnKU205l3dy2ur_nb2k" 

class AIPlotter:
    def __init__(self, root):
        self.root = root
        self.root.title("TÜBİTAK Projesi")
        self.root.geometry("1250x900")
        self.root.configure(bg="#f1f5f9")
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.colors = ['#2563eb', '#dc2626', '#16a34a', '#d97706', '#7c3aed', '#db2777']
        
        self.model_list = [
            "gemini-3.1-flash-lite-preview",
            "gemini-2.0-pro-exp-02-05",
            "gemini-2.0-flash-exp",
            "gemini-2.0-flash",
            "gemini-1.5-pro-002",
            "gemini-1.5-flash-002",
            "gemini-pro"
        ]
        
        # Hazır Şekiller Kütüphanesi
        self.preset_shapes = {
            "Üçgen": "{'x': 'np.where(t < 2*pi/3, 5*t/(2*pi/3), np.where(t < 4*pi/3, 5*(1 - 0.5*(t-2*pi/3)/(2*pi/3)), 2.5*(1 - (t-4*pi/3)/(2*pi/3))))', 'y': 'np.where(t < 2*pi/3, 0, np.where(t < 4*pi/3, 2.5*sqrt(3)*(t-2*pi/3)/(2*pi/3), 2.5*sqrt(3)*(1 - (t-4*pi/3)/(2*pi/3))))'}",            "Kare": "{'x': '5*sign(cos(t))*abs(cos(t))**0.1', 'y': '5*sign(sin(t))*abs(sin(t))**0.1'}",
            "Dikdörtgen": "{'x': '7*sign(cos(t))*abs(cos(t))**0.1', 'y': '4*sign(sin(t))*abs(sin(t))**0.1'}",
            "Karo": "{'x': '5*abs(cos(t))**2 * sign(cos(t))', 'y': '5*abs(sin(t))**2 * sign(sin(t))'}",
            "Çiçek": "{'x': 'cos(t)*(4 + 2*sin(6*t))', 'y': 'sin(t)*(4 + 2*sin(6*t))'}",
            "Çember": "{'x': '6*cos(t)', 'y': '6*sin(t)'}",
            "Elips": "{'x': '8*cos(t)', 'y': '4*sin(t)'}"
        }
        
        self.rows = [] 
        self.setup_ui()
        self.add_function_row("") 
        self.plot()

    def setup_ui(self):
        # Ana Konteyner
        self.main_container = tk.Frame(self.root, bg="#f1f5f9")
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Sol Panel
        self.sidebar = tk.Frame(self.main_container, width=400, bg="white", padx=20, pady=20)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="TÜBİTAK PROJESİ", font=("Segoe UI", 9, "bold"), bg="white", fg="#94a3b8").pack(anchor="w")
        tk.Label(self.sidebar, text="Matematik Motoru", font=("Segoe UI", 18, "bold"), bg="white", fg="#1e293b").pack(anchor="w", pady=(0, 10))

        # Hazır Şekiller Paneli
        preset_frame = tk.LabelFrame(self.sidebar, text=" 📐 Hazır Şekiller ", font=("Segoe UI", 10, "bold"), bg="#fdf2f8", fg="#db2777", padx=5, pady=5)
        preset_frame.pack(fill=tk.X, pady=(0, 15))

        grid_frame = tk.Frame(preset_frame, bg="#fdf2f8")
        grid_frame.pack(fill=tk.X)

        # Butonları 4x2 grid şeklinde yerleştir
        for i, (name, formula) in enumerate(self.preset_shapes.items()):
            btn = tk.Button(grid_frame, text=name, command=lambda f=formula: self.add_function_row(f), 
                           bg="white", fg="#db2777", font=("Segoe UI", 8, "bold"), 
                           relief="flat", borderwidth=1, cursor="hand2", padx=5, pady=2)
            btn.grid(row=i//4, column=i%4, sticky="nsew", padx=2, pady=2)
        
        for i in range(4): grid_frame.grid_columnconfigure(i, weight=1)

        # AI Giriş Alanı
        ai_frame = tk.LabelFrame(self.sidebar, text=" ✨ Yapay Zeka Komutu ", font=("Segoe UI", 10, "bold"), bg="#f8fafc", fg="#4f46e5", padx=10, pady=10)
        ai_frame.pack(fill=tk.X, pady=(0, 15))

        self.ai_entry = tk.Entry(ai_frame, font=("Segoe UI", 11), borderwidth=1, relief="solid")
        self.ai_entry.pack(fill=tk.X, pady=5, ipady=5)
        self.ai_entry.insert(0, "")

        self.ai_btn = tk.Button(ai_frame, text="AI İle Çiz / Oluştur", command=self.generate_ai_formula, bg="#4f46e5", fg="white", font=("Segoe UI", 10, "bold"), cursor="hand2", relief="flat", pady=8)
        self.ai_btn.pack(fill=tk.X, pady=5)

        # Fonksiyon Listesi
        list_header = tk.Frame(self.sidebar, bg="white")
        list_header.pack(fill=tk.X, pady=(10, 5))
        tk.Label(list_header, text="Fonksiyonlar", font=("Segoe UI", 11, "bold"), bg="white").pack(side=tk.LEFT)
        
        self.add_btn = tk.Button(list_header, text="+ Yeni Ekle", command=lambda: self.add_function_row(), bg="#10b981", fg="white", font=("Segoe UI", 8, "bold"), borderwidth=0, padx=8)
        self.add_btn.pack(side=tk.RIGHT)

        # Kaydırılabilir Fonksiyon Alanı
        self.func_scroll = tk.Canvas(self.sidebar, bg="white", highlightthickness=0)
        self.func_container = tk.Frame(self.func_scroll, bg="white")
        self.func_scroll.pack(fill=tk.BOTH, expand=True)
        self.func_scroll.create_window((0,0), window=self.func_container, anchor="nw")

        # Alt Butonlar
        self.update_btn = tk.Button(self.sidebar, text="Grafiği Güncelle", command=self.plot, bg="#1e293b", fg="white", font=("Segoe UI", 11, "bold"), pady=12, relief="flat")
        self.update_btn.pack(fill=tk.X, pady=(10, 0))
        
        self.clear_btn = tk.Button(self.sidebar, text="Tümünü Temizle", command=self.clear_all, bg="#ef4444", fg="white", font=("Segoe UI", 10), pady=5, relief="flat")
        self.clear_btn.pack(fill=tk.X, pady=5)

        # Sağ Panel (Grafik)
        self.graph_frame = tk.Frame(self.main_container, bg="white")
        self.graph_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.fig, self.ax = plt.subplots(figsize=(6, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.graph_frame)

    def on_closing(self):
        """Programı ve terminal sürecini tamamen kapatır."""
        self.root.destroy()
        sys.exit(0)

    def add_function_row(self, initial_val=""):
        idx = len(self.rows)
        row_frame = tk.Frame(self.func_container, bg="white")
        row_frame.pack(fill=tk.X, pady=2)
        
        v = tk.BooleanVar(value=True)
        cb = tk.Checkbutton(row_frame, variable=v, bg="white", command=self.plot)
        cb.pack(side=tk.LEFT)
        
        color = self.colors[idx % len(self.colors)]
        e = tk.Entry(row_frame, font=("Consolas", 10), fg=color, borderwidth=1, relief="solid")
        e.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        if initial_val: e.insert(0, initial_val)

        del_btn = tk.Button(row_frame, text="✕", command=lambda r=row_frame: self.remove_row(r), bg="white", fg="#cbd5e1", borderwidth=0, font=("Arial", 10), cursor="hand2")
        del_btn.pack(side=tk.RIGHT)
            
        self.rows.append({'frame': row_frame, 'entry': e, 'var': v})
        if initial_val: self.plot()

    def remove_row(self, frame):
        for i, row in enumerate(self.rows):
            if row['frame'] == frame:
                row['frame'].destroy()
                self.rows.pop(i)
                break
        self.plot()

    def clear_all(self):
        for row in self.rows: row['frame'].destroy()
        self.rows = []
        self.plot()

    def generate_ai_formula(self):
        user_input = self.ai_entry.get()
        if not user_input or not API_KEY: 
            messagebox.showwarning("Uyarı", "Lütfen komutunuzu kontrol edin.")
            return
        
        self.ai_btn.config(text="AI Yanıtlıyor...", state=tk.DISABLED)
        self.root.update()

        sys_prompt = (
            "Sen matematiksel bir grafik motorusun. "
            "Kullanıcı bir şekil istediğinde bunu 't' parametreli (0-2pi) JSON olarak döndür. "
            "YILDIZ ÖRNEĞİ: {'x': '5*(cos(t)*abs(cos(2.5*t))**0.8)', 'y': '5*(sin(t)*abs(cos(2.5*t))**0.8)'} "
            "Sadece saf JSON döndür. Asla açıklama yapma."
        )

        success = False
        last_error = ""

        for model in self.model_list:
            for ver in ["v1beta", "v1"]:
                url = f"https://generativelanguage.googleapis.com/{ver}/models/{model}:generateContent?key={API_KEY}"
                payload = {"contents": [{"parts": [{"text": f"{sys_prompt}\nİstek: {user_input}"}]}]}
                
                try:
                    resp = requests.post(url, json=payload, timeout=10)
                    data = resp.json()
                    if "candidates" in data:
                        raw = data['candidates'][0]['content']['parts'][0]['text']
                        clean = re.sub(r'```[a-z]*', '', raw).strip().replace('`', '')
                        self.add_function_row(clean)
                        success = True
                        break
                    else:
                        last_error = data.get('error', {}).get('message', 'Bilinmeyen Hata')
                except Exception as e:
                    last_error = str(e)
                    continue
            if success: break

        if not success:
            messagebox.showerror("Hata", f"Model yanıt vermedi.\nDetay: {last_error}")
        
        self.ai_btn.config(text="AI İle Çiz / Oluştur", state=tk.NORMAL)

    def plot(self):
        self.ax.clear()
        self.ax.grid(True, linestyle='--', alpha=0.5)
        self.ax.axhline(0, color='black', linewidth=1)
        self.ax.axvline(0, color='black', linewidth=1)
        
        t = np.linspace(0, 2*np.pi, 5000)
        x_vals = np.linspace(-10, 10, 2000)
        
        context = {
            'np': np, 'x': x_vals, 't': t, 'pi': np.pi,
            'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
            'abs': np.abs, 'sqrt': np.sqrt, 'exp': np.exp,
            'log': np.log, 'sign': np.sign, 'power': np.power,
            'floor': np.floor, 'ceil': np.ceil, 'arctan2': np.arctan2,
            'max': np.maximum, 'min': np.minimum
        }

        for row in self.rows:
            if not row['var'].get(): continue
            txt = row['entry'].get().replace('^', '**').strip()
            
            try:
                if '{' in txt and '}' in txt:
                    d = json.loads(txt.replace("'", '"'))
                    # Eval için context içinde max ve min desteği
                    px = eval(d['x'], {"__builtins__": None}, context)
                    py = eval(d['y'], {"__builtins__": None}, context)
                    self.ax.plot(px, py, linewidth=2.5)
                else:
                    y = eval(txt, {"__builtins__": None}, context)
                    if isinstance(y, (int, float)): y = np.full_like(x_vals, y)
                    self.ax.plot(x_vals, y, linewidth=2)
            except: continue

        self.ax.set_xlim(-10, 10)
        self.ax.set_ylim(-10, 10)
        self.ax.set_aspect('equal')
        self.canvas.draw()

if __name__ == "__main__":
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = AIPlotter(root)
    root.mainloop()