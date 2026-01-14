-- 3. Add a new record to the original DB
USE GalacticZoo;
INSERT INTO Species (CommonName, HomePlanet, DietType, ExhibitID, LeadKeeperID)
VALUES ('Time-Snail', 'Gallifrey', 'Lettuce/Chronons', 4, 3);

-- 4. Take a Differential Backup (The Incremental)
BACKUP DATABASE GalacticZoo
TO DISK = '/var/opt/mssql/data/GalacticZoo_Diff.bak'
WITH DIFFERENTIAL;
GO

-- 5. Apply the Differential
RESTORE DATABASE GalacticZoo_DR
FROM DISK = '/var/opt/mssql/data/GalacticZoo_Diff.bak'
WITH RECOVERY; -- This brings the DB online for use
GO

-- 6. Verify the Time-Snail made it to the DR site
SELECT * FROM GalacticZoo_DR.dbo.Species WHERE CommonName = 'Time-Snail';