// Документы групп: данные группы и вложенный состав студентов (агрегат читается одним запросом)
db.student_groups.insertMany([
  {
    "_id": "18216887-5128-552b-8269-fed53ee98175",
    "name": "БСБО-01-23",
    "enrollment_year": 2023,
    "course_year": 3,
    "curator": "Комарова Е.В.",
    "specialty": {
      "code": "38.03.05",
      "name": "Бизнес-информатика",
      "degree_level": "bachelor"
    },
    "department": {
      "short_name": "КИС",
      "name": "Кафедра корпоративных информационных систем"
    },
    "students_count": 25,
    "students": [
      {
        "id": "0abd7fcf-8a20-5394-b4b3-e3fc647063ab",
        "student_card_number": "23Б0101",
        "last_name": "Судовский",
        "first_name": "Андрей",
        "patronymic": "Леонидович",
        "email": "23b0101@edu.mirea.ru",
        "status": "active",
        "electives": [
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "83f000d3-69ce-5d1e-a5bc-27320e1747a4",
        "student_card_number": "23Б0102",
        "last_name": "Беляев",
        "first_name": "Даниил",
        "patronymic": "Михайлович",
        "email": "23b0102@edu.mirea.ru",
        "status": "active",
        "electives": [
          "NoSQL и полиглотное хранение"
        ]
      },
      {
        "id": "dbc362e7-a40c-5095-8343-bd5cb088d960",
        "student_card_number": "23Б0103",
        "last_name": "Волкова",
        "first_name": "Дарья",
        "patronymic": "Николаевна",
        "email": "23b0103@edu.mirea.ru",
        "status": "active",
        "electives": [
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "30effbc2-a7cf-5cd9-ac88-2a4565f9c730",
        "student_card_number": "23Б0104",
        "last_name": "Павлова",
        "first_name": "Ксения",
        "patronymic": "Олеговна",
        "email": "23b0104@edu.mirea.ru",
        "status": "active",
        "electives": [
          "NoSQL и полиглотное хранение"
        ]
      },
      {
        "id": "f009f22c-3034-5b09-bfc9-bfcfadc45830",
        "student_card_number": "23Б0105",
        "last_name": "Соколова",
        "first_name": "Виктория",
        "patronymic": "Александровна",
        "email": "23b0105@edu.mirea.ru",
        "status": "active",
        "electives": [
          "NoSQL и полиглотное хранение"
        ]
      },
      {
        "id": "6d3b02a3-17a9-5efa-b313-e00432f64937",
        "student_card_number": "23Б0106",
        "last_name": "Кузнецов",
        "first_name": "Егор",
        "patronymic": "Павлович",
        "email": "23b0106@edu.mirea.ru",
        "status": "active",
        "electives": [
          "NoSQL и полиглотное хранение",
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "a212ecbd-c504-5f5e-b87d-900f3ac9c22a",
        "student_card_number": "23Б0107",
        "last_name": "Богданова",
        "first_name": "Анна",
        "patronymic": "Романовна",
        "email": "23b0107@edu.mirea.ru",
        "status": "active",
        "electives": [
          "NoSQL и полиглотное хранение",
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "c7664fd4-a953-54fc-86cd-30b26a138f7b",
        "student_card_number": "23Б0108",
        "last_name": "Комаров",
        "first_name": "Егор",
        "patronymic": "Николаевич",
        "email": "23b0108@edu.mirea.ru",
        "status": "active",
        "electives": [
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "1024897a-b321-5831-9751-91bedca27749",
        "student_card_number": "23Б0109",
        "last_name": "Фёдоров",
        "first_name": "Кирилл",
        "patronymic": "Павлович",
        "email": "23b0109@edu.mirea.ru",
        "status": "active",
        "electives": [
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "3798ae31-5b72-5e4e-9f40-7544aacedea5",
        "student_card_number": "23Б0110",
        "last_name": "Семёнов",
        "first_name": "Егор",
        "patronymic": "Андреевич",
        "email": "23b0110@edu.mirea.ru",
        "status": "active",
        "electives": [
          "NoSQL и полиглотное хранение"
        ]
      },
      {
        "id": "636beab8-cc2a-55a5-a7df-23fda21cc8dd",
        "student_card_number": "23Б0111",
        "last_name": "Виноградов",
        "first_name": "Евгений",
        "patronymic": "Николаевич",
        "email": "23b0111@edu.mirea.ru",
        "status": "active",
        "electives": [
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "d523fd12-1ffd-5c77-bf6b-7e56af941091",
        "student_card_number": "23Б0112",
        "last_name": "Макаров",
        "first_name": "Егор",
        "patronymic": "Павлович",
        "email": "23b0112@edu.mirea.ru",
        "status": "active",
        "electives": [
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "c29b6f3c-3792-5c57-a866-50b0550060d3",
        "student_card_number": "23Б0113",
        "last_name": "Комарова",
        "first_name": "Ольга",
        "patronymic": "Николаевна",
        "email": "23b0113@edu.mirea.ru",
        "status": "active",
        "electives": [
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "6681bcbe-42ee-54d2-ae84-2cdf5113ffc8",
        "student_card_number": "23Б0114",
        "last_name": "Козлова",
        "first_name": "Софья",
        "patronymic": "Сергеевна",
        "email": "23b0114@edu.mirea.ru",
        "status": "active",
        "electives": [
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "cbf11f1d-826d-50cf-9b44-577fcbfd4a43",
        "student_card_number": "23Б0115",
        "last_name": "Беляев",
        "first_name": "Артём",
        "patronymic": "Андреевич",
        "email": "23b0115@edu.mirea.ru",
        "status": "active",
        "electives": [
          "NoSQL и полиглотное хранение",
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "a2e77b87-ad5a-5e6f-a899-c48d491e1e66",
        "student_card_number": "23Б0116",
        "last_name": "Соколов",
        "first_name": "Александр",
        "patronymic": "Иванович",
        "email": "23b0116@edu.mirea.ru",
        "status": "active",
        "electives": [
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "71b0ccd2-3ae9-56de-8e3b-7303d24a4a2e",
        "student_card_number": "23Б0117",
        "last_name": "Богданов",
        "first_name": "Андрей",
        "patronymic": "Романович",
        "email": "23b0117@edu.mirea.ru",
        "status": "active",
        "electives": [
          "NoSQL и полиглотное хранение"
        ]
      },
      {
        "id": "5bc51f24-1bee-5782-b5bb-68ec869cff64",
        "student_card_number": "23Б0118",
        "last_name": "Макарова",
        "first_name": "Виктория",
        "patronymic": "Павловна",
        "email": "23b0118@edu.mirea.ru",
        "status": "active",
        "electives": [
          "NoSQL и полиглотное хранение",
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "23c5d949-dcc0-59a3-a402-933771603c93",
        "student_card_number": "23Б0119",
        "last_name": "Семёнов",
        "first_name": "Максим",
        "patronymic": "Александрович",
        "email": "23b0119@edu.mirea.ru",
        "status": "active",
        "electives": [
          "NoSQL и полиглотное хранение"
        ]
      },
      {
        "id": "e4c7f639-3faa-59e4-9492-e6474a3795d8",
        "student_card_number": "23Б0120",
        "last_name": "Виноградов",
        "first_name": "Никита",
        "patronymic": "Дмитриевич",
        "email": "23b0120@edu.mirea.ru",
        "status": "active",
        "electives": [
          "NoSQL и полиглотное хранение",
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "18c45a4f-9817-5fbb-b67f-fc1ded545cf0",
        "student_card_number": "23Б0121",
        "last_name": "Голубев",
        "first_name": "Никита",
        "patronymic": "Николаевич",
        "email": "23b0121@edu.mirea.ru",
        "status": "active",
        "electives": [
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "f21ff00a-addc-5d25-859e-ad7edabaf8aa",
        "student_card_number": "23Б0122",
        "last_name": "Лебедев",
        "first_name": "Дмитрий",
        "patronymic": "Викторович",
        "email": "23b0122@edu.mirea.ru",
        "status": "active",
        "electives": [
          "NoSQL и полиглотное хранение",
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "0a07e916-3f5d-5c95-8d56-cc2ee53321a2",
        "student_card_number": "23Б0123",
        "last_name": "Белов",
        "first_name": "Александр",
        "patronymic": "Сергеевич",
        "email": "23b0123@edu.mirea.ru",
        "status": "active",
        "electives": [
          "NoSQL и полиглотное хранение",
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "303c982c-80c4-5c66-97b8-eaa77e4028ff",
        "student_card_number": "23Б0124",
        "last_name": "Лебедев",
        "first_name": "Роман",
        "patronymic": "Алексеевич",
        "email": "23b0124@edu.mirea.ru",
        "status": "active",
        "electives": [
          "NoSQL и полиглотное хранение"
        ]
      },
      {
        "id": "b5d20c82-52b8-52e6-84b0-fec7edff935c",
        "student_card_number": "23Б0125",
        "last_name": "Виноградова",
        "first_name": "Вероника",
        "patronymic": "Михайловна",
        "email": "23b0125@edu.mirea.ru",
        "status": "active",
        "electives": [
          "Бизнес-аналитика"
        ]
      }
    ]
  },
  {
    "_id": "1ec206d0-4903-52c9-ac2a-587bbf8879bf",
    "name": "БСБО-02-23",
    "enrollment_year": 2023,
    "course_year": 3,
    "curator": "Орлов П.С.",
    "specialty": {
      "code": "38.03.05",
      "name": "Бизнес-информатика",
      "degree_level": "bachelor"
    },
    "department": {
      "short_name": "КИС",
      "name": "Кафедра корпоративных информационных систем"
    },
    "students_count": 6,
    "students": [
      {
        "id": "856bbbba-4365-516c-8a6d-436a29ac7f2c",
        "student_card_number": "23Б0201",
        "last_name": "Воробьёв",
        "first_name": "Кирилл",
        "patronymic": "Дмитриевич",
        "email": "23b0201@edu.mirea.ru",
        "status": "active",
        "electives": [
          "NoSQL и полиглотное хранение",
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "7bb424ab-5f1b-5be0-a5cc-d70a9d5933b4",
        "student_card_number": "23Б0202",
        "last_name": "Макарова",
        "first_name": "Ирина",
        "patronymic": "Александровна",
        "email": "23b0202@edu.mirea.ru",
        "status": "active",
        "electives": [
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "faab4354-a894-5fa1-874d-4dc46686f67b",
        "student_card_number": "23Б0203",
        "last_name": "Кузнецов",
        "first_name": "Кирилл",
        "patronymic": "Павлович",
        "email": "23b0203@edu.mirea.ru",
        "status": "active",
        "electives": [
          "NoSQL и полиглотное хранение"
        ]
      },
      {
        "id": "e8904a71-e5c5-53b3-9e07-fecc611e0648",
        "student_card_number": "23Б0204",
        "last_name": "Лебедев",
        "first_name": "Сергей",
        "patronymic": "Викторович",
        "email": "23b0204@edu.mirea.ru",
        "status": "active",
        "electives": [
          "Бизнес-аналитика"
        ]
      },
      {
        "id": "480baba1-abe5-57f4-b1d6-c368291a5c25",
        "student_card_number": "23Б0205",
        "last_name": "Михайлова",
        "first_name": "Елена",
        "patronymic": "Алексеевна",
        "email": "23b0205@edu.mirea.ru",
        "status": "active",
        "electives": [
          "NoSQL и полиглотное хранение"
        ]
      },
      {
        "id": "712d0d3e-0d64-505c-85c0-53d7d59dfbc0",
        "student_card_number": "23Б0206",
        "last_name": "Киселёв",
        "first_name": "Кирилл",
        "patronymic": "Михайлович",
        "email": "23b0206@edu.mirea.ru",
        "status": "active",
        "electives": [
          "NoSQL и полиглотное хранение"
        ]
      }
    ]
  }
]);
