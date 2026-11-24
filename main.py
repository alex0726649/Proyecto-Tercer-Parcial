"""Aplicación de consola para administrar un blog en Neo4j.

Uso:
    python main.py
"""

from pathlib import Path

from app.blog import Blog
from app.db import Database

CYPHER_DIR = Path(__file__).parent / "cypher"


# ----------------------------------------------------------------- helpers
def ask(prompt, required=True):
    while True:
        value = input(f"{prompt}: ").strip()
        if value or not required:
            return value
        print("  * Este campo es obligatorio.")


def ask_list(prompt):
    raw = input(f"{prompt} (separados por coma, vacío = ninguno): ").strip()
    return [x.strip() for x in raw.split(",") if x.strip()]


def show_table(rows, columns):
    """Imprime una lista de diccionarios como tabla de texto."""
    if not rows:
        print("  (sin resultados)")
        return
    data = [[_fmt(r.get(c)) for c in columns] for r in rows]
    widths = [max(len(c), *(len(row[i]) for row in data)) for i, c in enumerate(columns)]
    line = " | ".join(c.ljust(w) for c, w in zip(columns, widths))
    print("  " + line)
    print("  " + "-+-".join("-" * w for w in widths))
    for row in data:
        print("  " + " | ".join(v.ljust(w) for v, w in zip(row, widths)))


def _fmt(value):
    if isinstance(value, list):
        return ", ".join(map(str, value))
    return "" if value is None else str(value)


def done(ok, ok_msg, fail_msg):
    print(f"  ✔ {ok_msg}" if ok else f"  ✘ {fail_msg}")


# ------------------------------------------------------------ menú: acciones
def users_menu(blog):
    print("\n-- USUARIOS --\n1) Crear  2) Listar  3) Editar  4) Eliminar  0) Volver")
    op = input("Opción: ").strip()
    if op == "1":
        user = blog.create_user(ask("Nombre"), ask("Email"))
        if user:
            print(f"  ✔ Usuario guardado: {user['name']} <{user['email']}>")
        else:
            print("  ✘ Ya existe un usuario con ese email (usa la opción 3 para editarlo).")
    elif op == "2":
        show_table(blog.list_users(), ["name", "email", "articles"])
    elif op == "3":
        user = blog.update_user(ask("Email del usuario"), ask("Nuevo nombre"))
        done(user, "Usuario actualizado.", "No existe ese usuario.")
    elif op == "4":
        done(blog.delete_user(ask("Email del usuario")),
             "Usuario eliminado (con sus artículos y comentarios).",
             "No existe ese usuario.")


def articles_menu(blog):
    print("\n-- ARTÍCULOS --\n1) Crear  2) Listar  3) Ver detalle  4) Editar  "
          "5) Eliminar\n6) Agregar tag  7) Quitar tag  8) Agregar categoría  "
          "9) Quitar categoría  0) Volver")
    op = input("Opción: ").strip()
    if op == "1":
        article_id = blog.create_article(
            ask("Email del autor"), ask("Título"), ask("Texto"),
            categories=ask_list("Categorías"), tags=ask_list("Tags"),
        )
        done(article_id, f"Artículo creado con id {article_id}.",
             "No existe un usuario con ese email.")
    elif op == "2":
        show_table(blog.list_articles(),
                   ["id", "title", "date", "author", "categories", "tags", "comments"])
    elif op == "3":
        a = blog.get_article(ask("Id del artículo"))
        if not a:
            print("  ✘ No existe ese artículo.")
            return
        print(f"\n  {a['title']}  ({a['date']}, por {a['author']})")
        print(f"  Categorías: {_fmt(a['categories'])} | Tags: {_fmt(a['tags'])}")
        print(f"\n  {a['text']}\n")
        print("  Comentarios:")
        show_table(a["comments"], ["id", "user", "name", "text"])
    elif op == "4":
        article_id = ask("Id del artículo")
        title = ask("Nuevo título (vacío = sin cambio)", required=False) or None
        text = ask("Nuevo texto (vacío = sin cambio)", required=False) or None
        done(blog.update_article(article_id, title, text),
             "Artículo actualizado.", "No existe ese artículo.")
    elif op == "5":
        done(blog.delete_article(ask("Id del artículo")),
             "Artículo eliminado junto con sus comentarios.", "No existe ese artículo.")
    elif op == "6":
        done(blog.add_tag(ask("Id del artículo"), ask("Tag")),
             "Tag asociado.", "No existe ese artículo.")
    elif op == "7":
        blog.remove_tag(ask("Id del artículo"), ask("Tag"))
        print("  ✔ Tag desasociado.")
    elif op == "8":
        done(blog.add_category(ask("Id del artículo"), ask("Categoría")),
             "Categoría asociada.", "No existe ese artículo.")
    elif op == "9":
        blog.remove_category(ask("Id del artículo"), ask("Categoría"))
        print("  ✔ Categoría desasociada.")


def comments_menu(blog):
    print("\n-- COMENTARIOS --\n1) Agregar  2) Listar por artículo  3) Eliminar  0) Volver")
    op = input("Opción: ").strip()
    if op == "1":
        cid = blog.add_comment(
            ask("Id del artículo"), ask("Email del usuario"),
            ask("Título del comentario"), ask("Texto", required=False),
        )
        done(cid, f"Comentario creado con id {cid}.",
             "Artículo o usuario inexistente.")
    elif op == "2":
        show_table(blog.list_comments(ask("Id del artículo")),
                   ["id", "user", "name", "text", "url"])
    elif op == "3":
        done(blog.delete_comment(ask("Id del comentario")),
             "Comentario eliminado.", "No existe ese comentario.")


def tags_categories_menu(blog):
    print("\n-- TAGS Y CATEGORÍAS --\n1) Listar tags  2) Listar categorías  0) Volver")
    op = input("Opción: ").strip()
    if op == "1":
        show_table(blog.list_tags(), ["name", "url", "articles"])
    elif op == "2":
        show_table(blog.list_categories(), ["name", "url", "articles"])


def queries_menu(blog):
    print("\n-- CONSULTAS --\n1) Por tag  2) Por categoría  3) Por usuario  "
          "4) Buscar texto\n5) Artículos relacionados  6) Estadísticas  0) Volver")
    op = input("Opción: ").strip()
    cols = ["id", "title", "date"]
    if op == "1":
        show_table(blog.articles_by_tag(ask("Tag")), cols)
    elif op == "2":
        show_table(blog.articles_by_category(ask("Categoría")), cols)
    elif op == "3":
        show_table(blog.articles_by_user(ask("Email del usuario")), cols)
    elif op == "4":
        show_table(blog.search(ask("Texto a buscar")), cols)
    elif op == "5":
        show_table(blog.related_articles(ask("Id del artículo")),
                   ["id", "title", "shared_tags"])
    elif op == "6":
        stats = blog.stats()
        for key, value in stats.items():
            print(f"  {key:<11}: {value}")


def admin_menu(db, blog):
    print("\n-- ADMINISTRACIÓN --\n1) Crear esquema (restricciones e índices)\n"
          "2) Cargar datos de ejemplo  3) Borrar todos los datos del blog  0) Volver")
    op = input("Opción: ").strip()
    if op == "1":
        n = db.run_script(CYPHER_DIR / "01_schema.cypher")
        print(f"  ✔ {n} sentencias ejecutadas.")
    elif op == "2":
        n = db.run_script(CYPHER_DIR / "02_seed.cypher")
        print(f"  ✔ {n} sentencias ejecutadas.")
    elif op == "3":
        if input("  Escribe BORRAR para confirmar: ").strip() == "BORRAR":
            blog.clear_all()
            print("  ✔ Datos del blog eliminados.")
        else:
            print("  Operación cancelada.")


# -------------------------------------------------------------------- main
def main():
    db = Database()
    try:
        db.verify()
    except Exception as exc:  # noqa: BLE001
        print(f"No se pudo conectar a Neo4j: {exc}")
        print("Revisa tu archivo .env (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD).")
        return

    blog = Blog(db)
    db.run_script(CYPHER_DIR / "01_schema.cypher")  # idempotente (IF NOT EXISTS)

    menus = {
        "1": lambda: users_menu(blog),
        "2": lambda: articles_menu(blog),
        "3": lambda: comments_menu(blog),
        "4": lambda: tags_categories_menu(blog),
        "5": lambda: queries_menu(blog),
        "6": lambda: admin_menu(db, blog),
    }
    try:
        while True:
            print("\n========= BLOG · Neo4j =========")
            print("1) Usuarios      2) Artículos     3) Comentarios")
            print("4) Tags/Categorías  5) Consultas  6) Administración")
            print("0) Salir")
            op = input("Opción: ").strip()
            if op == "0":
                break
            action = menus.get(op)
            if action:
                try:
                    action()
                except Exception as exc:  # noqa: BLE001
                    print(f"  ✘ Error: {exc}")
            else:
                print("  Opción no válida.")
    finally:
        db.close()
        print("Hasta luego.")


if __name__ == "__main__":
    main()
