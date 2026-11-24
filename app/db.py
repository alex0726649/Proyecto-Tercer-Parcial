"""Conexión a Neo4j y utilidades para ejecutar archivos Cypher."""

import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


class Database:
    """Envuelve el driver de Neo4j con métodos simples de lectura y escritura."""

    def __init__(self, uri=URI, user=USER, password=PASSWORD, database=DATABASE):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._database = database

    def verify(self):
        """Lanza una excepción si no hay conexión con el servidor."""
        self._driver.verify_connectivity()

    def close(self):
        self._driver.close()

    def read(self, query, **params):
        """Ejecuta una consulta de lectura y devuelve una lista de diccionarios."""
        with self._driver.session(database=self._database) as session:
            return session.execute_read(
                lambda tx: [r.data() for r in tx.run(query, **params)]
            )

    def write(self, query, **params):
        """Ejecuta una consulta de escritura y devuelve una lista de diccionarios."""
        with self._driver.session(database=self._database) as session:
            return session.execute_write(
                lambda tx: [r.data() for r in tx.run(query, **params)]
            )

    def run_script(self, path):
        """Ejecuta un archivo .cypher; las sentencias se separan por ';'."""
        text = Path(path).read_text(encoding="utf-8")
        # Quita comentarios de línea completa antes de separar sentencias.
        lines = [l for l in text.splitlines() if not l.strip().startswith("//")]
        statements = [s.strip() for s in "\n".join(lines).split(";") if s.strip()]
        for stmt in statements:
            self.write(stmt)
        return len(statements)
