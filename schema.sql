CREATE DATABASE IF NOT EXISTS library_analysis CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE library_analysis;
CREATE TABLE IF NOT EXISTS books (
 id INT AUTO_INCREMENT PRIMARY KEY, title VARCHAR(200) NOT NULL, author VARCHAR(160) NOT NULL,
 isbn VARCHAR(40) UNIQUE, category VARCHAR(80) DEFAULT 'General', total_copies INT NOT NULL DEFAULT 1,
 available_copies INT NOT NULL DEFAULT 1, damaged_copies INT NOT NULL DEFAULT 0, missing_copies INT NOT NULL DEFAULT 0, cover_url VARCHAR(500) DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 CHECK(total_copies >= 0), CHECK(available_copies >= 0 AND available_copies <= total_copies)
);
CREATE TABLE IF NOT EXISTS borrowers (
 id INT AUTO_INCREMENT PRIMARY KEY, full_name VARCHAR(160) NOT NULL, email VARCHAR(190) DEFAULT '',
 is_active TINYINT(1) NOT NULL DEFAULT 1, borrow_limit INT NOT NULL DEFAULT 3, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS loans (
 id INT AUTO_INCREMENT PRIMARY KEY, book_id INT NOT NULL, borrower_id INT NULL, borrower_name VARCHAR(160) NOT NULL,
 issue_date DATE NOT NULL, due_date DATE NOT NULL, return_date DATE NULL, status ENUM('Issued','Returned') NOT NULL DEFAULT 'Issued',
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE RESTRICT,
 FOREIGN KEY(borrower_id) REFERENCES borrowers(id) ON DELETE SET NULL
);
INSERT IGNORE INTO books(title,author,isbn,category,total_copies,available_copies) VALUES
('The Alchemist','Paulo Coelho','9780061122415','Fiction',4,4),
('Wings of Fire','A. P. J. Abdul Kalam','9788173711466','Biography',3,3),
('Atomic Habits','James Clear','9780735211292','Self-help',5,5),
('Clean Code','Robert C. Martin','9780132350884','Technology',2,2),
('The Hobbit','J. R. R. Tolkien','9780547928227','Fantasy',3,3),
('Introduction to Algorithms','Thomas H. Cormen','9780262046305','Technology',2,2);

CREATE TABLE IF NOT EXISTS reservations (
 id INT AUTO_INCREMENT PRIMARY KEY, book_id INT NOT NULL, borrower_name VARCHAR(160) NOT NULL, email VARCHAR(190) DEFAULT '',
 status ENUM('Pending','Approved','Rejected','Fulfilled') NOT NULL DEFAULT 'Pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE
);
