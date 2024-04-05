PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE User( id integer primary key autoincrement, discord_id text not null, name text default "Ẩn sĩ", email text not null, unique(id, discord_id, email));
CREATE TABLE Deadline(
  id integer primary key autoincrement,
  url text not null,
  created_at timestamp default (datetime('now', 'localtime')),
  name text not null,
  unique(id, url)
);
DELETE FROM sqlite_sequence;
COMMIT;
