import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import unicodedata
import os
import json

def normalizar_nome(nome):
    nome = unicodedata.normalize('NFKD', nome)
    nome = ''.join(c for c in nome if not unicodedata.combining(c))
    return nome.strip().lower()

def carregar_json_jogadores_times(caminho_json):
    try:
        with open(caminho_json, "r", encoding="utf-8") as f:
            dados = json.load(f)
        jogadores_times = {}
        for time in dados:
            nome_time = time.get("nome", "Sem Time")
            lista_jogadores = time.get("jogadores", [])
            for jogador in lista_jogadores:
                nome_normalizado = normalizar_nome(jogador)
                jogadores_times[nome_normalizado] = nome_time
        return jogadores_times
    except Exception as e:
        print(f"Erro ao carregar JSON: {e}")  # debug no console
        messagebox.showerror("Erro", f"Erro ao carregar JSON de jogadores:\n{e}")
        return {}

def traduzir(col):
    traducoes = {
        "Jogador": "Jogador",
        "Kills": "Abates",
        "Assists": "Assistências",
        "Damage Dealt": "Dano Causado",
    }
    return traducoes.get(col, col)

class App:
    def __init__(self, root):
        self.root = root
        root.title("📊 Visualizador CSV Agrupado")
        root.geometry("900x600")
        root.configure(bg="#f2f2f2")

        self.df_total = pd.DataFrame()
        self.ordem_coluna = {}

        estilo = ttk.Style()
        estilo.theme_use("clam")
        estilo.configure("Treeview", font=("Segoe UI", 9))
        estilo.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

        frame_topo = ttk.Frame(root)
        frame_topo.pack(fill='x', pady=8)

        ttk.Button(frame_topo, text="📂 Abrir Pasta CSV", command=self.abrir_pasta_csv).pack(side='left', padx=8)
        ttk.Button(frame_topo, text="💾 Salvar Filtro JSON", command=self.salvar_filtro).pack(side='left', padx=8)
        ttk.Button(frame_topo, text="❌ Fechar", command=root.quit).pack(side='right', padx=8)

        # Frame do filtro por time
        filtro_frame = ttk.Frame(root)
        filtro_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(filtro_frame, text="Filtrar por Time: ").pack(side='left')
        self.combo_times = ttk.Combobox(filtro_frame, state="readonly")
        self.combo_times.pack(side='left')
        self.combo_times.bind("<<ComboboxSelected>>", lambda e: self.atualizar_tabela())

        frame_tabela = ttk.Frame(root)
        frame_tabela.pack(expand=True, fill='both', padx=10, pady=10)

        self.scroll_x = ttk.Scrollbar(frame_tabela, orient='horizontal')
        self.scroll_x.pack(side='top', fill='x')
        self.scroll_y = ttk.Scrollbar(frame_tabela, orient='vertical')
        self.scroll_y.pack(side='right', fill='y')

        self.tree = ttk.Treeview(frame_tabela, xscrollcommand=self.scroll_x.set, yscrollcommand=self.scroll_y.set)
        self.tree.pack(expand=True, fill='both')
        self.scroll_x.config(command=self.tree.xview)
        self.scroll_y.config(command=self.tree.yview)

        self.jogadores_times = {}

        # Ajuste aqui para pegar o JSON na mesma pasta do script
        pasta_script = os.path.dirname(os.path.abspath(__file__))
        caminho_json = os.path.join(pasta_script, "jogadores_times.json")

        if os.path.exists(caminho_json):
            self.jogadores_times = carregar_json_jogadores_times(caminho_json)
            print(f"JSON carregado automaticamente com {len(self.jogadores_times)} jogadores.")
        else:
            messagebox.showwarning("Aviso", "Arquivo JSON de jogadores não encontrado.")
            self.jogadores_times = {}

    def abrir_pasta_csv(self):
        pasta = filedialog.askdirectory()
        if not pasta:
            return

        arquivos = [os.path.join(pasta, f) for f in os.listdir(pasta) if f.endswith(".csv")]
        if not arquivos:
            messagebox.showwarning("Aviso", "Nenhum arquivo CSV encontrado na pasta.")
            return

        lista_dfs = []
        for arquivo in arquivos:
            try:
                df = pd.read_csv(arquivo)
                lista_dfs.append(df)
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao ler {arquivo}:\n{e}")
                return

        df_concatenado = pd.concat(lista_dfs, ignore_index=True)
        self.df_total_original = df_concatenado
        self.df_total = self.agregar_dados(df_concatenado)

        self.atualizar_combobox()
        self.atualizar_tabela()

    def agregar_dados(self, df):
        df["Nome Normalizado"] = df["Name"].apply(normalizar_nome)
        df["Name"] = df["Name"].str.replace(r"\s*\*$", "", regex=True)

        # Aplica o time usando o JSON, ou 'Sem Time' caso não tenha
        df["Time"] = df["Nome Normalizado"].apply(lambda x: self.jogadores_times.get(x, "Sem Time"))

        grouped = df.groupby(["Nome Normalizado", "Time"], dropna=False).agg({
            "Name": "first",
            "Kills": "sum",
            "Assists": "sum",
            "Damage Dealt": "sum"
        }).reset_index()

        grouped.rename(columns={"Name": "Jogador"}, inplace=True)

        # Colunas para exibir (não mostramos o time na tabela, só para filtro)
        grouped = grouped[["Jogador", "Kills", "Assists", "Damage Dealt", "Time"]]
        return grouped

    def atualizar_combobox(self):
        if self.df_total.empty:
            self.combo_times['values'] = ["Todos"]
            self.combo_times.set("Todos")
            return

        times = sorted(self.df_total["Time"].dropna().unique())
        self.combo_times['values'] = ["Todos"] + times
        self.combo_times.set("Todos")

    def atualizar_tabela(self, ordenar_por=None):
        if self.df_total.empty:
            return

        filtro_time = self.combo_times.get()
        if filtro_time and filtro_time != "Todos":
            df = self.df_total[self.df_total["Time"] == filtro_time]
        else:
            df = self.df_total

        if ordenar_por:
            crescente = self.ordem_coluna.get(ordenar_por, True)
            try:
                df = df.sort_values(by=ordenar_por, ascending=crescente)
                self.ordem_coluna[ordenar_por] = not crescente
            except Exception:
                pass

        self.tree.delete(*self.tree.get_children())
        colunas = ["Jogador", "Kills", "Assists", "Damage Dealt"]
        self.tree["columns"] = [traduzir(c) for c in colunas]
        self.tree["show"] = "headings"

        for c in colunas:
            self.tree.heading(traduzir(c), text=traduzir(c), command=lambda c=c: self.atualizar_tabela(ordenar_por=c))
            self.tree.column(traduzir(c), width=140, anchor='w')

        for _, row in df.iterrows():
            self.tree.insert("", "end", values=[row[c] for c in colunas])

    def salvar_filtro(self):
        if self.df_total.empty:
            messagebox.showinfo("Info", "Nenhum dado para salvar.")
            return

        filtro_time = self.combo_times.get()

        # Filtra o dataframe de acordo com o filtro selecionado
        if filtro_time and filtro_time != "Todos":
            df_filtrado = self.df_total[self.df_total["Time"] == filtro_time]
        else:
            df_filtrado = self.df_total

        # Agrupa por time e estrutura os dados no formato desejado
        resultado = []
        for time, grupo in df_filtrado.groupby("Time"):
            jogadores = []
            for _, row in grupo.iterrows():
                jogadores.append({
                    "jogador": row["Jogador"],
                    "abates": int(row["Kills"]),
                    "assistencias": int(row["Assists"]),
                    "dano": int(row["Damage Dealt"]),
                })
            resultado.append({
                "time": time,
                "jogadores": jogadores
            })

        caminho = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not caminho:
            return

        try:
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(resultado, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Sucesso", "Dados salvos em JSON com sucesso.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar o JSON:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
