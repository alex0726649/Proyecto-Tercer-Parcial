// =========================================================
// 04_updates.cypher - Ejemplos de actualización y borrado
// ¡CUIDADO! Estas sentencias MODIFICAN o ELIMINAN datos.
// Ejecútalas una por una y solo si quieres probarlas.
// Para restaurar los datos: vuelve a cargar 02_seed.cypher.
// =========================================================

// 1. Actualizar un artículo
MATCH (a:Article {id: 'art-001'})
SET a.title = 'Introducción a Neo4j (actualizado)'
RETURN a;

// 2. Eliminar un comentario
MATCH (c:Comment {id: 'com-002'})
DETACH DELETE c;

// 3. Eliminar un artículo junto con sus comentarios
MATCH (a:Article {id: 'art-002'})
OPTIONAL MATCH (a)-[:HAS_COMMENT]->(c:Comment)
DETACH DELETE c, a;
