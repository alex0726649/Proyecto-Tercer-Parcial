"""Interfaz gráfica (Tkinter) para administrar el blog en Neo4j.

Uso:
    python gui.py
"""

import functools
import math
import random
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from app.blog import Blog
from app.db import Database

CYPHER_DIR = Path(__file__).parent / "cypher"

HEADINGS = {
    "id": "Id", "title": "Título", "date": "Fecha", "author": "Autor",
    "categories": "Categorías", "tags": "Tags", "comments": "Comentarios",
    "name": "Nombre", "email": "Email", "articles": "Artículos",
    "user": "Usuario", "text": "Texto", "url": "URL",
    "shared_tags": "Tags en común", "métrica": "Métrica", "valor": "Valor",
}

NODE_COLORS = {
    "User": "#4C78A8", "Article": "#F58518", "Comment": "#54A24B",
    "Tag": "#B279A2", "Category": "#E45756",
}


# --------------------------------------------------------------- utilidades
def fmt(value):
    if isinstance(value, list):
        return ", ".join(map(str, value))
    return "" if value is None else str(value)


def split_list(raw):
    return [x.strip() for x in raw.split(",") if x.strip()]


def guarded(fn):
    """Muestra un cuadro de error si la operación falla."""
    @functools.wraps(fn)
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", str(exc))
    return wrapper


def spring_layout(ids, edges, width, height, iterations=200, seed=7):
    """Distribución de nodos tipo Fruchterman-Reingold (sin dependencias)."""
    rnd = random.Random(seed)
    pad = 50
    pos = {i: [rnd.uniform(pad, width - pad), rnd.uniform(pad, height - pad)]
           for i in ids}
    if len(ids) < 2:
        return pos
    if len(ids) > 150:
        iterations = 60
    k = math.sqrt((width - 2 * pad) * (height - 2 * pad) / len(ids)) * 0.8
    temp = width / 10
    ordered = sorted(ids)
    for _ in range(iterations):
        disp = {i: [0.0, 0.0] for i in ids}
        for idx, a in enumerate(ordered):
            for b in ordered[idx + 1:]:
                dx = pos[a][0] - pos[b][0]
                dy = pos[a][1] - pos[b][1]
                dist = max(math.hypot(dx, dy), 0.01)
                force = k * k / dist
                fx, fy = dx / dist * force, dy / dist * force
                disp[a][0] += fx; disp[a][1] += fy
                disp[b][0] -= fx; disp[b][1] -= fy
        for src, dst in edges:
            if src not in pos or dst not in pos:
                continue
            dx = pos[src][0] - pos[dst][0]
            dy = pos[src][1] - pos[dst][1]
            dist = max(math.hypot(dx, dy), 0.01)
            force = dist * dist / k
            fx, fy = dx / dist * force, dy / dist * force
            disp[src][0] -= fx; disp[src][1] -= fy
            disp[dst][0] += fx; disp[dst][1] += fy
        for i in ids:
            dx, dy = disp[i]
            dist = max(math.hypot(dx, dy), 0.01)
            step = min(dist, temp)
            pos[i][0] = min(width - pad, max(pad, pos[i][0] + dx / dist * step))
            pos[i][1] = min(height - pad, max(pad, pos[i][1] + dy / dist * step))
        temp *= 0.97
    return pos


class Table(ttk.Frame):
    """Treeview con scroll que trabaja con listas de diccionarios."""

    def __init__(self, parent, columns, height=10, on_select=None):
        super().__init__(parent)
        self.columns = columns
        self._rows = []
        self.tree = ttk.Treeview(self, columns=columns, show="headings",
                                 height=height, selectmode="browse")
        for col in columns:
            self.tree.heading(col, text=HEADINGS.get(col, col))
            self.tree.column(col, width=110, anchor="w")
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        if on_select:
            self.tree.bind("<<TreeviewSelect>>", lambda _e: on_select(self.selected()))

    def set_rows(self, rows):
        self.tree.delete(*self.tree.get_children())
        self._rows = list(rows)
        for i, row in enumerate(self._rows):
            self.tree.insert("", "end", iid=str(i),
                             values=[fmt(row.get(c)) for c in self.columns])

    def selected(self):
        sel = self.tree.selection()
        return self._rows[int(sel[0])] if sel else None


# ---------------------------------------------------------------- aplicación
class BlogApp:
    def __init__(self, root, db):
        self.root = root
        self.db = db
        self.blog = Blog(db)
        self.user_map = {}
        self.article_map = {}
        self.selected_article = None

        root.title("Blog · Neo4j")
        root.geometry("1150x700")
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")

        self.status = tk.StringVar(value="Conectado a Neo4j.")
        ttk.Label(root, textvariable=self.status, anchor="w",
                  relief="sunken").pack(side="bottom", fill="x")

        self.nb = ttk.Notebook(root)
        self.nb.pack(fill="both", expand=True)
        tabs = [
            ("Usuarios", self.build_users),
            ("Artículos", self.build_articles),
            ("Comentarios", self.build_comments),
            ("Tags y categorías", self.build_tags),
            ("Consultas", self.build_queries),
            ("Grafo", self.build_graph),
            ("Administración", self.build_admin),
        ]
        self.tab_frames = {}
        for title, builder in tabs:
            frame = ttk.Frame(self.nb)
            self.nb.add(frame, text=title)
            self.tab_frames[title] = frame
            builder(frame)
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.refresh_all()

    # ------------------------------------------------------------ comunes
    def info(self, message):
        self.status.set(message)

    def warn(self, message):
        messagebox.showwarning("Faltan datos", message)

    def field(self, parent, label, var, row, col=0, width=30):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=4, pady=3)
        entry = ttk.Entry(parent, textvariable=var, width=width)
        entry.grid(row=row, column=col + 1, sticky="we", padx=4, pady=3)
        return entry

    @guarded
    def refresh_all(self):
        users = self.blog.list_users()
        self.users_table.set_rows(users)
        self.user_map = {f"{u['name']} <{u['email']}>": u["email"] for u in users}
        labels = sorted(self.user_map)
        self.a_author["values"] = labels
        self.c_user["values"] = labels

        articles = self.blog.list_articles()
        self.art_table.set_rows(articles)
        self.article_map = {f"{a['id']} — {a['title']}": a["id"] for a in articles}
        self.c_article["values"] = list(self.article_map)

        self.tags_table.set_rows(self.blog.list_tags())
        self.cats_table.set_rows(self.blog.list_categories())
        self.load_comments()

    def on_tab_changed(self, _event):
        if self.nb.select() == str(self.tab_frames["Grafo"]):
            self.root.after(50, self.draw_graph)

    # ------------------------------------------------------------ usuarios
    def build_users(self, tab):
        form = ttk.LabelFrame(tab, text="Usuario")
        form.pack(side="left", fill="y", padx=8, pady=8)
        self.u_name, self.u_email = tk.StringVar(), tk.StringVar()
        self.field(form, "Nombre", self.u_name, 0)
        self.field(form, "Email", self.u_email, 1)
        buttons = ttk.Frame(form)
        buttons.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(buttons, text="Guardar nuevo", command=self.user_save).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Actualizar nombre", command=self.user_update).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Eliminar", command=self.user_delete).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Limpiar", command=self.user_clear).pack(fill="x", pady=2)
        self.users_table = Table(tab, ["name", "email", "articles"], height=18,
                                 on_select=self.fill_user)
        self.users_table.pack(side="left", fill="both", expand=True, padx=8, pady=8)

    def fill_user(self, row):
        if row:
            self.u_name.set(row["name"])
            self.u_email.set(row["email"])

    def user_clear(self):
        self.u_name.set("")
        self.u_email.set("")

    @guarded
    def user_save(self):
        name, email = self.u_name.get().strip(), self.u_email.get().strip()
        if not name or not email:
            return self.warn("Escribe nombre y email.")
        if not self.blog.create_user(name, email):
            return self.warn("Ya existe un usuario con ese email.\n"
                             "Para cambiarle el nombre usa «Actualizar nombre».")
        self.refresh_all()
        self.info(f"Usuario guardado: {name}")

    @guarded
    def user_update(self):
        name, email = self.u_name.get().strip(), self.u_email.get().strip()
        if not name or not email:
            return self.warn("Selecciona un usuario y escribe el nuevo nombre.")
        if self.blog.update_user(email, name):
            self.refresh_all()
            self.info("Usuario actualizado.")
        else:
            self.warn("No existe un usuario con ese email.")

    @guarded
    def user_delete(self):
        email = self.u_email.get().strip()
        if not email:
            return self.warn("Selecciona un usuario.")
        if not messagebox.askyesno(
                "Confirmar", f"¿Eliminar a {email} junto con sus artículos y comentarios?"):
            return
        if self.blog.delete_user(email):
            self.user_clear()
            self.refresh_all()
            self.info("Usuario eliminado.")
        else:
            self.warn("No existe un usuario con ese email.")

    # ----------------------------------------------------------- artículos
    def build_articles(self, tab):
        self.art_table = Table(
            tab, ["id", "title", "date", "author", "categories", "tags", "comments"],
            height=9, on_select=self.fill_article)
        self.art_table.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        form = ttk.LabelFrame(tab, text="Artículo")
        form.pack(fill="x", padx=8, pady=4)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)
        self.a_title, self.a_cats, self.a_tags = tk.StringVar(), tk.StringVar(), tk.StringVar()

        ttk.Label(form, text="Autor").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        self.a_author = ttk.Combobox(form, state="readonly", width=34)
        self.a_author.grid(row=0, column=1, sticky="we", padx=4, pady=3)
        self.field(form, "Título", self.a_title, 0, col=2)
        self.field(form, "Categorías (coma)", self.a_cats, 1, col=0)
        self.field(form, "Tags (coma)", self.a_tags, 1, col=2)
        ttk.Label(form, text="Texto").grid(row=2, column=0, sticky="nw", padx=4, pady=3)
        self.a_text = tk.Text(form, height=4, wrap="word")
        self.a_text.grid(row=2, column=1, columnspan=3, sticky="we", padx=4, pady=3)

        buttons = ttk.Frame(form)
        buttons.grid(row=3, column=0, columnspan=4, pady=6)
        for label, cmd in [
            ("Crear", self.article_create),
            ("Actualizar título/texto", self.article_update),
            ("Eliminar", self.article_delete),
            ("+ Categorías/Tags", self.article_add_labels),
            ("− Categorías/Tags", self.article_remove_labels),
            ("Ver detalle", self.article_detail),
            ("Limpiar", self.article_clear),
        ]:
            ttk.Button(buttons, text=label, command=cmd).pack(side="left", padx=3)

    @guarded
    def fill_article(self, row):
        if not row:
            return
        self.selected_article = row["id"]
        article = self.blog.get_article(row["id"])
        if not article:
            return
        self.a_title.set(article["title"])
        self.a_cats.set(", ".join(article["categories"]))
        self.a_tags.set(", ".join(article["tags"]))
        self.a_text.delete("1.0", "end")
        self.a_text.insert("1.0", article["text"] or "")

    def article_clear(self):
        self.selected_article = None
        self.a_title.set("")
        self.a_cats.set("")
        self.a_tags.set("")
        self.a_text.delete("1.0", "end")

    def _need_article(self):
        if not self.selected_article:
            self.warn("Selecciona un artículo de la tabla.")
            return False
        return True

    @guarded
    def article_create(self):
        email = self.user_map.get(self.a_author.get())
        title = self.a_title.get().strip()
        text = self.a_text.get("1.0", "end").strip()
        if not email or not title or not text:
            return self.warn("Elige un autor y escribe título y texto.")
        article_id = self.blog.create_article(
            email, title, text,
            categories=split_list(self.a_cats.get()), tags=split_list(self.a_tags.get()))
        if not article_id:
            return self.warn("No se pudo crear el artículo (autor inexistente).")
        self.article_clear()
        self.refresh_all()
        self.info(f"Artículo creado: {article_id}")

    @guarded
    def article_update(self):
        if not self._need_article():
            return
        title = self.a_title.get().strip() or None
        text = self.a_text.get("1.0", "end").strip() or None
        if self.blog.update_article(self.selected_article, title, text):
            self.refresh_all()
            self.info("Artículo actualizado.")

    @guarded
    def article_delete(self):
        if not self._need_article():
            return
        if not messagebox.askyesno("Confirmar", "¿Eliminar el artículo y sus comentarios?"):
            return
        if self.blog.delete_article(self.selected_article):
            self.article_clear()
            self.refresh_all()
            self.info("Artículo eliminado.")

    @guarded
    def article_add_labels(self):
        if not self._need_article():
            return
        for name in split_list(self.a_cats.get()):
            self.blog.add_category(self.selected_article, name)
        for name in split_list(self.a_tags.get()):
            self.blog.add_tag(self.selected_article, name)
        self.refresh_all()
        self.info("Categorías y tags asociados al artículo.")

    @guarded
    def article_remove_labels(self):
        if not self._need_article():
            return
        for name in split_list(self.a_cats.get()):
            self.blog.remove_category(self.selected_article, name)
        for name in split_list(self.a_tags.get()):
            self.blog.remove_tag(self.selected_article, name)
        self.refresh_all()
        self.info("Categorías y tags desasociados del artículo.")

    @guarded
    def article_detail(self):
        if not self._need_article():
            return
        article = self.blog.get_article(self.selected_article)
        if not article:
            return
        win = tk.Toplevel(self.root)
        win.title(article["title"])
        box = tk.Text(win, wrap="word", width=80, height=24, padx=10, pady=10)
        box.pack(fill="both", expand=True)
        box.insert("end", f"{article['title']}\n", "title")
        box.insert("end", f"{article['date']} · por {article['author']}\n")
        box.insert("end", f"Categorías: {fmt(article['categories'])}\n")
        box.insert("end", f"Tags: {fmt(article['tags'])}\n\n")
        box.insert("end", f"{article['text']}\n\nComentarios ({len(article['comments'])}):\n")
        for c in article["comments"]:
            box.insert("end", f"  • {c['user']}: {c['name']} — {c['text']}\n")
        box.tag_configure("title", font=("TkDefaultFont", 14, "bold"))
        box.configure(state="disabled")

    # ---------------------------------------------------------- comentarios
    def build_comments(self, tab):
        form = ttk.LabelFrame(tab, text="Comentario")
        form.pack(fill="x", padx=8, pady=8)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)
        self.c_name, self.c_text = tk.StringVar(), tk.StringVar()

        ttk.Label(form, text="Artículo").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        self.c_article = ttk.Combobox(form, state="readonly", width=40)
        self.c_article.grid(row=0, column=1, sticky="we", padx=4, pady=3)
        self.c_article.bind("<<ComboboxSelected>>", lambda _e: self.load_comments())
        ttk.Label(form, text="Usuario").grid(row=0, column=2, sticky="w", padx=4, pady=3)
        self.c_user = ttk.Combobox(form, state="readonly", width=34)
        self.c_user.grid(row=0, column=3, sticky="we", padx=4, pady=3)
        self.field(form, "Título", self.c_name, 1, col=0)
        self.field(form, "Texto", self.c_text, 1, col=2)

        buttons = ttk.Frame(form)
        buttons.grid(row=2, column=0, columnspan=4, pady=6)
        ttk.Button(buttons, text="Agregar comentario", command=self.comment_add).pack(side="left", padx=3)
        ttk.Button(buttons, text="Eliminar seleccionado", command=self.comment_delete).pack(side="left", padx=3)

        self.comments_table = Table(tab, ["id", "user", "name", "text", "url"], height=15)
        self.comments_table.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    @guarded
    def load_comments(self):
        article_id = self.article_map.get(self.c_article.get())
        rows = self.blog.list_comments(article_id) if article_id else []
        self.comments_table.set_rows(rows)

    @guarded
    def comment_add(self):
        article_id = self.article_map.get(self.c_article.get())
        email = self.user_map.get(self.c_user.get())
        name = self.c_name.get().strip()
        if not article_id or not email or not name:
            return self.warn("Elige artículo y usuario, y escribe el título del comentario.")
        cid = self.blog.add_comment(article_id, email, name, self.c_text.get().strip())
        if not cid:
            return self.warn("No se pudo crear el comentario.")
        self.c_name.set("")
        self.c_text.set("")
        self.refresh_all()
        self.info(f"Comentario creado: {cid}")

    @guarded
    def comment_delete(self):
        row = self.comments_table.selected()
        if not row:
            return self.warn("Selecciona un comentario de la tabla.")
        if messagebox.askyesno("Confirmar", "¿Eliminar el comentario seleccionado?"):
            self.blog.delete_comment(row["id"])
            self.refresh_all()
            self.info("Comentario eliminado.")

    # ---------------------------------------------------- tags y categorías
    def build_tags(self, tab):
        left = ttk.LabelFrame(tab, text="Tags")
        left.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        right = ttk.LabelFrame(tab, text="Categorías")
        right.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        self.tags_table = Table(left, ["name", "url", "articles"], height=18)
        self.tags_table.pack(fill="both", expand=True, padx=4, pady=4)
        self.cats_table = Table(right, ["name", "url", "articles"], height=18)
        self.cats_table.pack(fill="both", expand=True, padx=4, pady=4)

    # ------------------------------------------------------------ consultas
    def build_queries(self, tab):
        art = ["id", "title", "date"]
        self.queries = {
            "Artículos por tag": (self.blog.articles_by_tag, art, "Tag"),
            "Artículos por categoría": (self.blog.articles_by_category, art, "Categoría"),
            "Artículos por usuario": (self.blog.articles_by_user, art, "Email del usuario"),
            "Buscar texto": (self.blog.search, art, "Texto a buscar"),
            "Artículos relacionados": (self.blog.related_articles,
                                       ["id", "title", "shared_tags"], "Id del artículo"),
            "Estadísticas": (lambda _p: [{"métrica": k, "valor": v}
                                         for k, v in self.blog.stats().items()],
                             ["métrica", "valor"], ""),
        }
        bar = ttk.Frame(tab)
        bar.pack(fill="x", padx=8, pady=8)
        ttk.Label(bar, text="Consulta").pack(side="left")
        self.q_combo = ttk.Combobox(bar, state="readonly", values=list(self.queries), width=28)
        self.q_combo.current(0)
        self.q_combo.pack(side="left", padx=6)
        self.q_hint = tk.StringVar()
        ttk.Label(bar, textvariable=self.q_hint).pack(side="left", padx=(10, 2))
        self.q_param = tk.StringVar()
        ttk.Entry(bar, textvariable=self.q_param, width=30).pack(side="left", padx=4)
        ttk.Button(bar, text="Ejecutar", command=self.run_query).pack(side="left", padx=6)
        self.q_combo.bind("<<ComboboxSelected>>", lambda _e: self._update_hint())
        self._update_hint()
        self.q_frame = ttk.Frame(tab)
        self.q_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.q_table = None

    def _update_hint(self):
        hint = self.queries[self.q_combo.get()][2]
        self.q_hint.set(f"{hint}:" if hint else "(sin parámetro)")

    @guarded
    def run_query(self):
        fn, columns, hint = self.queries[self.q_combo.get()]
        param = self.q_param.get().strip()
        if hint and not param:
            return self.warn(f"Escribe: {hint}.")
        rows = fn(param)
        if self.q_table:
            self.q_table.destroy()
        self.q_table = Table(self.q_frame, columns, height=18)
        self.q_table.pack(fill="both", expand=True)
        self.q_table.set_rows(rows)
        self.info(f"{len(rows)} resultado(s).")

    # ---------------------------------------------------------------- grafo
    def build_graph(self, tab):
        bar = ttk.Frame(tab)
        bar.pack(fill="x", padx=8, pady=6)
        ttk.Button(bar, text="Actualizar grafo", command=self.draw_graph).pack(side="left")
        for label, color in NODE_COLORS.items():
            swatch = tk.Label(bar, text=f"  {label}  ", bg=color, fg="white")
            swatch.pack(side="left", padx=(12, 0))
        self.canvas = tk.Canvas(tab, bg="white", highlightthickness=1,
                                highlightbackground="#cccccc")
        self.canvas.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    @guarded
    def draw_graph(self):
        data = self.blog.graph()
        canvas = self.canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 600)
        height = max(canvas.winfo_height(), 400)
        nodes, edges = data["nodes"], data["edges"]
        if not nodes:
            canvas.create_text(width / 2, height / 2, text="No hay datos del blog.",
                               fill="#888888", font=("TkDefaultFont", 14))
            return
        ids = [n["id"] for n in nodes]
        pos = spring_layout(ids, [(e["src"], e["dst"]) for e in edges], width, height)
        radius = 18

        for edge in edges:
            if edge["src"] not in pos or edge["dst"] not in pos:
                continue
            x1, y1 = pos[edge["src"]]
            x2, y2 = pos[edge["dst"]]
            dist = max(math.hypot(x2 - x1, y2 - y1), 0.01)
            ux, uy = (x2 - x1) / dist, (y2 - y1) / dist
            canvas.create_line(x1 + ux * radius, y1 + uy * radius,
                               x2 - ux * radius, y2 - uy * radius,
                               fill="#999999", arrow=tk.LAST)
            canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=edge["type"],
                               fill="#777777", font=("TkDefaultFont", 7))
        for node in nodes:
            x, y = pos[node["id"]]
            color = NODE_COLORS.get(node["label"], "#888888")
            canvas.create_oval(x - radius, y - radius, x + radius, y + radius,
                               fill=color, outline="white", width=2)
            canvas.create_text(x, y, text=node["label"][0], fill="white",
                               font=("TkDefaultFont", 10, "bold"))
            caption = str(node["caption"] or "")
            caption = caption if len(caption) <= 20 else caption[:19] + "…"
            canvas.create_text(x, y + radius + 9, text=caption,
                               font=("TkDefaultFont", 8))
        self.info(f"Grafo: {len(nodes)} nodos, {len(edges)} relaciones.")

    # -------------------------------------------------------- administración
    def build_admin(self, tab):
        box = ttk.LabelFrame(tab, text="Base de datos")
        box.pack(anchor="nw", padx=12, pady=12)
        for label, cmd in [
            ("Crear esquema (restricciones e índices)", self.admin_schema),
            ("Cargar datos de ejemplo", self.admin_seed),
            ("Refrescar datos", self.refresh_all),
            ("Borrar todos los datos del blog", self.admin_clear),
        ]:
            ttk.Button(box, text=label, command=cmd, width=42).pack(padx=10, pady=5)

    @guarded
    def admin_schema(self):
        n = self.db.run_script(CYPHER_DIR / "01_schema.cypher")
        self.info(f"Esquema creado ({n} sentencias).")

    @guarded
    def admin_seed(self):
        n = self.db.run_script(CYPHER_DIR / "02_seed.cypher")
        self.refresh_all()
        self.info(f"Datos de ejemplo cargados ({n} sentencias).")

    @guarded
    def admin_clear(self):
        if not messagebox.askyesno(
                "Confirmar",
                "Esto borra todos los usuarios, artículos, comentarios, tags y "
                "categorías del blog.\n¿Continuar?",
                icon="warning"):
            return
        self.blog.clear_all()
        self.article_clear()
        self.refresh_all()
        self.info("Datos del blog eliminados.")


# -------------------------------------------------------------------- main
def main():
    root = tk.Tk()
    db = Database()
    try:
        db.verify()
        db.run_script(CYPHER_DIR / "01_schema.cypher")  # idempotente
    except Exception as exc:  # noqa: BLE001
        messagebox.showerror(
            "No se pudo conectar a Neo4j",
            f"{exc}\n\nRevisa tu archivo .env (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD).")
        root.destroy()
        return

    BlogApp(root, db)

    def on_close():
        db.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
