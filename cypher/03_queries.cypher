// =========================================================
// 03_queries.cypher - Consultas de lectura sobre el blog
// (no modifican datos; se pueden ejecutar completas)
// =========================================================

// 1. Artículos con su autor, categorías y tags
MATCH (u:User)-[:WROTE]->(a:Article)
OPTIONAL MATCH (a)-[:IN_CATEGORY]->(c:Category)
OPTIONAL MATCH (a)-[:TAGGED_WITH]->(t:Tag)
RETURN a.title AS articulo, u.name AS autor,
       collect(DISTINCT c.name) AS categorias,
       collect(DISTINCT t.name) AS tags
ORDER BY a.date DESC;

// 2. Comentarios de un artículo
MATCH (a:Article {id: 'art-001'})-[:HAS_COMMENT]->(c:Comment)<-[:COMMENTED]-(u:User)
RETURN c.name AS comentario, c.text AS texto, u.name AS usuario;

// 3. Artículos por tag
MATCH (a:Article)-[:TAGGED_WITH]->(:Tag {name: 'neo4j'})
RETURN a.title AS articulo, a.date AS fecha;

// 4. Artículos por categoría
MATCH (a:Article)-[:IN_CATEGORY]->(:Category {name: 'Bases de datos'})
RETURN a.title AS articulo;

// 5. Usuarios con más artículos publicados
MATCH (u:User)-[:WROTE]->(a:Article)
RETURN u.name AS usuario, count(a) AS articulos
ORDER BY articulos DESC;

// 6. Tags más usados
MATCH (t:Tag)<-[:TAGGED_WITH]-(a:Article)
RETURN t.name AS tag, count(a) AS usos
ORDER BY usos DESC;

// 7. Artículos relacionados (comparten tags con art-002)
MATCH (:Article {id: 'art-002'})-[:TAGGED_WITH]->(t:Tag)<-[:TAGGED_WITH]-(otro:Article)
RETURN otro.title AS articulo, count(t) AS tags_en_comun
ORDER BY tags_en_comun DESC;

// 8. Búsqueda de texto en título o contenido
MATCH (a:Article)
WHERE toLower(a.title) CONTAINS 'python' OR toLower(a.text) CONTAINS 'python'
RETURN a.title AS articulo;
