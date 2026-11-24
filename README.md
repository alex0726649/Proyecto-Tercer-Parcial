# Blog en Neo4j con Python

Aplicación en Python (interfaz gráfica y consola) para administrar un blog sobre una base de datos de grafos **Neo4j**.
Proyecto de *Bases de Datos Avanzadas* (modalidad en equipo).

## Modelo del grafo

```
(User)-[:WROTE]->(Article)
(User)-[:COMMENTED]->(Comment)
(Article)-[:HAS_COMMENT]->(Comment)      1 artículo → N comentarios
(Article)-[:TAGGED_WITH]->(Tag)          N-N
(Article)-[:IN_CATEGORY]->(Category)     N-N
```

| Nodo       | Propiedades                                   |
|------------|-----------------------------------------------|
| `User`     | `name`, `email` (único)                       |
| `Article`  | `id` (único), `title`, `date`, `text`         |
| `Comment`  | `id` (único), `name`, `url`, `text`           |
| `Tag`      | `name` (único), `url`                         |
| `Category` | `name` (único), `url`                         |

> `Comment.text` se agregó como propiedad extra para guardar el contenido del comentario.

## Estructura

```
blog-neo4j/
├── gui.py                  # interfaz gráfica (Tkinter)
├── main.py                 # menú de consola
├── app/
│   ├── db.py               # conexión a Neo4j y ejecución de scripts .cypher
│   └── blog.py             # CRUD y consultas del blog
├── cypher/
│   ├── 01_schema.cypher    # restricciones e índices
│   ├── 02_seed.cypher      # datos de ejemplo
│   ├── 03_queries.cypher   # consultas de lectura (no modifican datos)
│   └── 04_updates.cypher   # ejemplos de actualización y borrado (¡modifican datos!)
├── requirements.txt
└── .env.example
```

## Requisitos

- Python 3.10 o superior
- Neo4j 5.x en ejecución (Neo4j Desktop, AuraDB o Docker)

Con Docker:

```bash
docker run -d --name neo4j-blog -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/cambia_esta_clave neo4j:5
```

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # edita la contraseña
python gui.py                    # interfaz gráfica
python main.py                   # alternativa: menú de consola
```

> Tkinter viene incluido con Python en Windows y macOS. En Linux (Debian/Ubuntu) instálalo con `sudo apt install python3-tk`.

## Interfaz gráfica

La ventana tiene siete pestañas:

| Pestaña | Qué hace |
|---|---|
| Usuarios | Crear, actualizar nombre y eliminar usuarios |
| Artículos | Crear con categorías y tags, editar, eliminar, ver detalle, asociar y desasociar tags/categorías |
| Comentarios | Agregar y eliminar comentarios por artículo |
| Tags y categorías | Listado con el número de artículos de cada uno |
| Consultas | Por tag, categoría o usuario; búsqueda de texto; artículos relacionados; estadísticas |
| Grafo | Dibuja los nodos y relaciones, con un color por tipo de nodo |
| Administración | Crear esquema, cargar datos de ejemplo, borrar los datos del blog |

## Uso

1. El esquema se crea automáticamente al iniciar.
2. En la pestaña **Administración** (o en el menú 6 de la consola) elige **Cargar datos de ejemplo**.
3. Usa el menú para administrar usuarios, artículos, comentarios, tags y categorías.
4. Las opciones de **Consultas** muestran recorridos del grafo (artículos relacionados por tags, búsqueda de texto, estadísticas).

Los archivos de `cypher/` también se pueden pegar directamente en Neo4j Browser (`http://localhost:7474`).

## Funcionalidades

- **Usuarios:** crear (avisa si el email ya existe), listar, editar y eliminar (en cascada: sus artículos y comentarios).
- **Artículos:** crear con categorías y tags, listar, ver detalle, editar, eliminar (con sus comentarios).
- **Comentarios:** agregar, listar por artículo, eliminar.
- **Tags y categorías:** asociar y desasociar a artículos (relación N-N), listar con conteo de uso. Las categorías no distinguen mayúsculas ni acentos ("tecnologia" = "Tecnología").
- **Aislamiento:** la vista de grafo y el borrado solo usan nodos del blog (`User`, `Article`, `Comment`, `Tag`, `Category`), así que la app puede compartir la base con otros datos sin afectarlos.
- **Consultas:** por tag, categoría o usuario; búsqueda por texto; artículos relacionados; estadísticas.
