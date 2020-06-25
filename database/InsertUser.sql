INSERT INTO "main"."users"
("username", "email", "password", "isAdmin", "lastTimeSeen", "TotalImagesScanned", "detectPid", "scanProgress", "trainPid", "trainProgress")
VALUES ('Administrator', 'Admin@yahoo.com', 'pbkdf2:sha256:150000$Cn3J5MI7$bc56ad6a0530036970755b9f0e8454c594aa2b1194e8f6d400d0dec439b94540', 1, '2020-06-15 10:10:57.10558', 100,-1,-1,-1,-1),
('Username', 'User@yahoo.com', 'pbkdf2:sha256:150000$9KkPlast$dd23c922f571873961343cfdb72fac0fcd429f74d2161981cefeeac01fff03a7', 0,'2020-06-15 10:00:57.10558', 10,-1,-1,-1,-1);