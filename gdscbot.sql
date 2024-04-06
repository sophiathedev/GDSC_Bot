PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE User( id integer primary key autoincrement, discord_id text unique not null, name text unique default "Ẩn sĩ", email text unique not null);
CREATE TABLE Deadline(
  id integer primary key autoincrement,
  url text not null,
  created_at timestamp default (datetime('now', 'localtime')),
  name text not null,
  unique(id, url)
);
DELETE FROM sqlite_sequence;
COMMIT;
