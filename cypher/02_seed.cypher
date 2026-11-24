// =========================================================
// 02_seed.cypher - Datos de ejemplo del blog
// Modelo:
//   (User)-[:WROTE]->(Article)
//   (User)-[:COMMENTED]->(Comment)
//   (Article)-[:HAS_COMMENT]->(Comment)
//   (Article)-[:TAGGED_WITH]->(Tag)
//   (Article)-[:IN_CATEGORY]->(Category)
// =========================================================

// Usuarios
MERGE (u1:User {email: 'ana@example.com'})  SET u1.name = 'Ana López'
MERGE (u2:User {email: 'luis@example.com'}) SET u2.name = 'Luis Pérez'
MERGE (u3:User {email: 'maria@example.com'}) SET u3.name = 'María Gómez';

// Categorías
MERGE (c1:Category {name: 'Tecnología'}) SET c1.url = '/categories/tecnologia'
MERGE (c2:Category {name: 'Bases de datos'}) SET c2.url = '/categories/bases-de-datos'
MERGE (c3:Category {name: 'Programación'}) SET c3.url = '/categories/programacion';

// Tags
MERGE (t1:Tag {name: 'neo4j'})  SET t1.url = '/tags/neo4j'
MERGE (t2:Tag {name: 'grafos'}) SET t2.url = '/tags/grafos'
MERGE (t3:Tag {name: 'python'}) SET t3.url = '/tags/python'
MERGE (t4:Tag {name: 'cypher'}) SET t4.url = '/tags/cypher';

// Artículos
MATCH (u:User {email: 'ana@example.com'})
MERGE (a:Article {id: 'art-001'})
  SET a.title = 'Introducción a Neo4j', a.date = date('2026-11-01'),
      a.text = 'Neo4j es una base de datos orientada a grafos que modela datos como nodos y relaciones.'
MERGE (u)-[:WROTE]->(a)
WITH a
MATCH (c:Category {name: 'Bases de datos'}), (t1:Tag {name: 'neo4j'}), (t2:Tag {name: 'grafos'})
MERGE (a)-[:IN_CATEGORY]->(c)
MERGE (a)-[:TAGGED_WITH]->(t1)
MERGE (a)-[:TAGGED_WITH]->(t2);

MATCH (u:User {email: 'luis@example.com'})
MERGE (a:Article {id: 'art-002'})
  SET a.title = 'Neo4j con Python', a.date = date('2026-11-05'),
      a.text = 'El driver oficial de Neo4j permite ejecutar consultas Cypher desde Python.'
MERGE (u)-[:WROTE]->(a)
WITH a
MATCH (c1:Category {name: 'Programación'}), (c2:Category {name: 'Bases de datos'}),
      (t1:Tag {name: 'neo4j'}), (t3:Tag {name: 'python'}), (t4:Tag {name: 'cypher'})
MERGE (a)-[:IN_CATEGORY]->(c1)
MERGE (a)-[:IN_CATEGORY]->(c2)
MERGE (a)-[:TAGGED_WITH]->(t1)
MERGE (a)-[:TAGGED_WITH]->(t3)
MERGE (a)-[:TAGGED_WITH]->(t4);

// Comentarios
MATCH (u:User {email: 'maria@example.com'}), (a:Article {id: 'art-001'})
MERGE (c:Comment {id: 'com-001'})
  SET c.name = 'Gran introducción', c.url = '/comments/com-001',
      c.text = 'Muy claro, gracias por compartirlo.'
MERGE (u)-[:COMMENTED]->(c)
MERGE (a)-[:HAS_COMMENT]->(c);

MATCH (u:User {email: 'ana@example.com'}), (a:Article {id: 'art-002'})
MERGE (c:Comment {id: 'com-002'})
  SET c.name = 'Buen ejemplo', c.url = '/comments/com-002',
      c.text = 'Me sirvió para mi proyecto de bases de datos.'
MERGE (u)-[:COMMENTED]->(c)
MERGE (a)-[:HAS_COMMENT]->(c);
