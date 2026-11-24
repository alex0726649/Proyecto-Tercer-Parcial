"""Operaciones del blog sobre Neo4j (CRUD y consultas).

Modelo del grafo:
    (User)-[:WROTE]->(Article)
    (User)-[:COMMENTED]->(Comment)
    (Article)-[:HAS_COMMENT]->(Comment)
    (Article)-[:TAGGED_WITH]->(Tag)
    (Article)-[:IN_CATEGORY]->(Category)
"""

import unicodedata
import uuid
from datetime import date

from .db import Database

# Etiquetas que pertenecen al blog. Las operaciones globales (dibujar el grafo,
# borrar la base) solo tocan estos nodos, para no afectar otros datos que
# existan en la misma base (por ejemplo, de otras prácticas).
BLOG_LABELS = ["User", "Article", "Comment", "Tag", "Category"]


def _new_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _normalize(text):
    """Minúsculas y sin acentos: 'Tecnología' -> 'tecnologia'."""
    decomposed = unicodedata.normalize("NFD", text.strip().lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _slug(text):
    """Texto para URL: 'Bases de datos' -> 'bases-de-datos'."""
    return "-".join(_normalize(text).split())


class Blog:
    def __init__(self, db: Database):
        self.db = db

    # ------------------------------------------------------------ usuarios
    def create_user(self, name, email):
        """Crea un usuario nuevo.

        Devuelve None si ya existe un usuario con ese email, en lugar de
        cambiarle el nombre sin avisar (para eso está update_user).
        """
        rows = self.db.write(
            """
            OPTIONAL MATCH (existing:User {email: $email})
            WITH existing WHERE existing IS NULL
            CREATE (u:User {email: $email, name: $name})
            RETURN u.name AS name, u.email AS email
            """,
            name=name, email=email,
        )
        return rows[0] if rows else None

    def list_users(self):
        return self.db.read(
            """
            MATCH (u:User)
            OPTIONAL MATCH (u)-[:WROTE]->(a:Article)
            RETURN u.name AS name, u.email AS email, count(a) AS articles
            ORDER BY name
            """
        )

    def update_user(self, email, name):
        rows = self.db.write(
            """
            MATCH (u:User {email: $email})
            SET u.name = $name
            RETURN u.name AS name, u.email AS email
            """,
            email=email, name=name,
        )
        return rows[0] if rows else None

    def delete_user(self, email):
        """Borra al usuario, sus comentarios y sus artículos (con comentarios)."""
        rows = self.db.write(
            """
            MATCH (u:User {email: $email})
            OPTIONAL MATCH (u)-[:COMMENTED]->(c:Comment)
            OPTIONAL MATCH (u)-[:WROTE]->(a:Article)
            OPTIONAL MATCH (a)-[:HAS_COMMENT]->(ac:Comment)
            DETACH DELETE c, ac, a, u
            RETURN count(u) AS deleted
            """,
            email=email,
        )
        return bool(rows and rows[0]["deleted"])

    # ----------------------------------------------------------- artículos
    def create_article(self, author_email, title, text, categories=(), tags=()):
        """Crea el artículo del autor y asocia sus categorías y tags (N-N)."""
        rows = self.db.write(
            """
            MATCH (u:User {email: $email})
            CREATE (a:Article {id: $id, title: $title, text: $text, date: date($date)})
            CREATE (u)-[:WROTE]->(a)
            RETURN a.id AS id
            """,
            email=author_email,
            id=_new_id("art"),
            title=title,
            text=text,
            date=date.today().isoformat(),
        )
        if not rows:
            return None
        article_id = rows[0]["id"]
        for name in categories:
            self.add_category(article_id, name)
        for name in tags:
            self.add_tag(article_id, name)
        return article_id

    def list_articles(self):
        return self.db.read(
            """
            MATCH (u:User)-[:WROTE]->(a:Article)
            OPTIONAL MATCH (a)-[:IN_CATEGORY]->(c:Category)
            OPTIONAL MATCH (a)-[:TAGGED_WITH]->(t:Tag)
            OPTIONAL MATCH (a)-[:HAS_COMMENT]->(cm:Comment)
            RETURN a.id AS id, a.title AS title, toString(a.date) AS date,
                   u.name AS author,
                   collect(DISTINCT c.name) AS categories,
                   collect(DISTINCT t.name) AS tags,
                   count(DISTINCT cm) AS comments
            ORDER BY date DESC, title
            """
        )

    def get_article(self, article_id):
        rows = self.db.read(
            """
            MATCH (u:User)-[:WROTE]->(a:Article {id: $id})
            OPTIONAL MATCH (a)-[:IN_CATEGORY]->(c:Category)
            OPTIONAL MATCH (a)-[:TAGGED_WITH]->(t:Tag)
            RETURN a.id AS id, a.title AS title, a.text AS text,
                   toString(a.date) AS date, u.name AS author,
                   collect(DISTINCT c.name) AS categories,
                   collect(DISTINCT t.name) AS tags
            """,
            id=article_id,
        )
        if not rows:
            return None
        article = rows[0]
        article["comments"] = self.list_comments(article_id)
        return article

    def update_article(self, article_id, title=None, text=None):
        rows = self.db.write(
            """
            MATCH (a:Article {id: $id})
            SET a.title = coalesce($title, a.title),
                a.text  = coalesce($text, a.text)
            RETURN a.id AS id, a.title AS title
            """,
            id=article_id, title=title, text=text,
        )
        return rows[0] if rows else None

    def delete_article(self, article_id):
        rows = self.db.write(
            """
            MATCH (a:Article {id: $id})
            OPTIONAL MATCH (a)-[:HAS_COMMENT]->(c:Comment)
            DETACH DELETE c, a
            RETURN count(a) AS deleted
            """,
            id=article_id,
        )
        return bool(rows and rows[0]["deleted"])

    # --------------------------------------------------------- comentarios
    def add_comment(self, article_id, user_email, name, text=""):
        cid = _new_id("com")
        rows = self.db.write(
            """
            MATCH (u:User {email: $email}), (a:Article {id: $article_id})
            CREATE (c:Comment {id: $cid, name: $name, text: $text,
                               url: '/comments/' + $cid})
            CREATE (u)-[:COMMENTED]->(c)
            CREATE (a)-[:HAS_COMMENT]->(c)
            RETURN c.id AS id
            """,
            email=user_email, article_id=article_id,
            cid=cid, name=name, text=text,
        )
        return rows[0]["id"] if rows else None

    def list_comments(self, article_id):
        return self.db.read(
            """
            MATCH (:Article {id: $id})-[:HAS_COMMENT]->(c:Comment)<-[:COMMENTED]-(u:User)
            RETURN c.id AS id, c.name AS name, c.text AS text,
                   c.url AS url, u.name AS user
            ORDER BY c.id
            """,
            id=article_id,
        )

    def delete_comment(self, comment_id):
        rows = self.db.write(
            """
            MATCH (c:Comment {id: $id})
            DETACH DELETE c
            RETURN 1 AS deleted
            """,
            id=comment_id,
        )
        return bool(rows)

    # ----------------------------------------------- tags y categorías (N-N)
    def add_tag(self, article_id, name):
        rows = self.db.write(
            """
            MATCH (a:Article {id: $id})
            MERGE (t:Tag {name: $name})
              ON CREATE SET t.url = '/tags/' + toLower(replace($name, ' ', '-'))
            MERGE (a)-[:TAGGED_WITH]->(t)
            RETURN t.name AS name
            """,
            id=article_id, name=name.strip().lower(),
        )
        return bool(rows)

    def remove_tag(self, article_id, name):
        self.db.write(
            """
            MATCH (:Article {id: $id})-[r:TAGGED_WITH]->(:Tag {name: $name})
            DELETE r
            """,
            id=article_id, name=name.strip().lower(),
        )

    def _resolve_category(self, name):
        """Devuelve el nombre de la categoría existente que coincide con `name`
        sin distinguir mayúsculas ni acentos, o `name` si no existe ninguna.

        Así "tecnologia", "Tecnologia" y "Tecnología" son la misma categoría.
        """
        name = name.strip()
        key = _normalize(name)
        for row in self.db.read("MATCH (c:Category) RETURN c.name AS name"):
            if _normalize(row["name"]) == key:
                return row["name"]
        return name

    def add_category(self, article_id, name):
        """Asocia una categoría al artículo (relación N-N), reutilizando la
        categoría existente si ya hay una equivalente."""
        cat_name = self._resolve_category(name)
        rows = self.db.write(
            """
            MATCH (a:Article {id: $id})
            MERGE (c:Category {name: $name})
              ON CREATE SET c.url = '/categories/' + $slug
            MERGE (a)-[:IN_CATEGORY]->(c)
            RETURN c.name AS name
            """,
            id=article_id, name=cat_name, slug=_slug(cat_name),
        )
        return bool(rows)

    def remove_category(self, article_id, name):
        self.db.write(
            """
            MATCH (:Article {id: $id})-[r:IN_CATEGORY]->(:Category {name: $name})
            DELETE r
            """,
            id=article_id, name=self._resolve_category(name),
        )

    def list_tags(self):
        return self.db.read(
            """
            MATCH (t:Tag)
            OPTIONAL MATCH (t)<-[:TAGGED_WITH]-(a:Article)
            RETURN t.name AS name, t.url AS url, count(a) AS articles
            ORDER BY articles DESC, name
            """
        )

    def list_categories(self):
        return self.db.read(
            """
            MATCH (c:Category)
            OPTIONAL MATCH (c)<-[:IN_CATEGORY]-(a:Article)
            RETURN c.name AS name, c.url AS url, count(a) AS articles
            ORDER BY articles DESC, name
            """
        )

    # ------------------------------------------------------------ consultas
    def articles_by_tag(self, tag):
        return self.db.read(
            """
            MATCH (a:Article)-[:TAGGED_WITH]->(:Tag {name: $tag})
            RETURN a.id AS id, a.title AS title, toString(a.date) AS date
            ORDER BY a.date DESC
            """,
            tag=tag.strip().lower(),
        )

    def articles_by_category(self, category):
        return self.db.read(
            """
            MATCH (a:Article)-[:IN_CATEGORY]->(:Category {name: $category})
            RETURN a.id AS id, a.title AS title, toString(a.date) AS date
            ORDER BY a.date DESC
            """,
            category=self._resolve_category(category),
        )

    def articles_by_user(self, email):
        return self.db.read(
            """
            MATCH (:User {email: $email})-[:WROTE]->(a:Article)
            RETURN a.id AS id, a.title AS title, toString(a.date) AS date
            ORDER BY a.date DESC
            """,
            email=email,
        )

    def search(self, term):
        return self.db.read(
            """
            MATCH (a:Article)
            WHERE toLower(a.title) CONTAINS toLower($term)
               OR toLower(a.text)  CONTAINS toLower($term)
            RETURN a.id AS id, a.title AS title, toString(a.date) AS date
            ORDER BY a.date DESC
            """,
            term=term,
        )

    def related_articles(self, article_id):
        """Artículos que comparten tags con el indicado (recorrido del grafo)."""
        return self.db.read(
            """
            MATCH (:Article {id: $id})-[:TAGGED_WITH]->(t:Tag)<-[:TAGGED_WITH]-(o:Article)
            RETURN o.id AS id, o.title AS title, count(t) AS shared_tags
            ORDER BY shared_tags DESC, title
            """,
            id=article_id,
        )

    def stats(self):
        return self.db.read(
            """
            CALL { MATCH (u:User)     RETURN count(u)  AS users }
            CALL { MATCH (a:Article)  RETURN count(a)  AS articles }
            CALL { MATCH (c:Comment)  RETURN count(c)  AS comments }
            CALL { MATCH (t:Tag)      RETURN count(t)  AS tags }
            CALL { MATCH (g:Category) RETURN count(g)  AS categories }
            RETURN users, articles, comments, tags, categories
            """
        )[0]

    def graph(self):
        """Nodos y relaciones del blog (para dibujarlos en la GUI).

        Solo incluye nodos con etiquetas del blog (BLOG_LABELS).
        """
        nodes = self.db.read(
            """
            MATCH (n)
            WHERE any(l IN labels(n) WHERE l IN $labels)
            RETURN elementId(n) AS id,
                   [l IN labels(n) WHERE l IN $labels][0] AS label,
                   coalesce(n.title, n.name) AS caption
            """,
            labels=BLOG_LABELS,
        )
        edges = self.db.read(
            """
            MATCH (a)-[r]->(b)
            WHERE any(l IN labels(a) WHERE l IN $labels)
              AND any(l IN labels(b) WHERE l IN $labels)
            RETURN elementId(a) AS src, elementId(b) AS dst, type(r) AS type
            """,
            labels=BLOG_LABELS,
        )
        return {"nodes": nodes, "edges": edges}

    def clear_all(self):
        """Borra todos los datos del blog. No toca nodos de otras etiquetas."""
        self.db.write(
            """
            MATCH (n)
            WHERE any(l IN labels(n) WHERE l IN $labels)
            DETACH DELETE n
            """,
            labels=BLOG_LABELS,
        )
