// Создание хранилища: коллекция с проверкой структуры документа и уникальным индексом по названию группы
db.createCollection("student_groups", {
  validator: { $jsonSchema: {
    bsonType: "object",
    required: ["name", "enrollment_year", "specialty", "students"],
    properties: {
      name:            { bsonType: "string", pattern: "^[А-ЯЁ]{4}-[0-9]{2}-[0-9]{2}$" },
      enrollment_year: { bsonType: "number", minimum: 2000 },
      students:        { bsonType: "array", items: { bsonType: "object",
                         required: ["student_card_number", "last_name", "first_name"] } }
    }
  } }
});
db.student_groups.createIndex({ name: 1 }, { unique: true });
