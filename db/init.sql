CREATE TABLE students (
  id SERIAL PRIMARY KEY,
  name TEXT,
  course TEXT,
  mark INTEGER
);

INSERT INTO students (name, course, mark) VALUES
('Alice Zhang', 'COMP1531', 85),
('Bob Smith', 'COMP1531', 72),
('Charlie Nguyen', 'COMP2521', 91),
('Dana Lee', 'COMP1511', 67);
