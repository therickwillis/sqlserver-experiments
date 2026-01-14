-- 1. Create a Full Backup
BACKUP DATABASE GalacticZoo 
TO DISK = '/var/opt/mssql/data/GalacticZoo_Full.bak' 
WITH FORMAT, MEDIANAME = 'ZooBackups', NAME = 'Full Backup of GalacticZoo';
GO

-- 2. Restore as a new DB, keeping it open for more data (NORECOVERY)
RESTORE DATABASE GalacticZoo_DR
FROM DISK = '/var/opt/mssql/data/GalacticZoo_Full.bak'
WITH MOVE 'GalacticZoo' TO '/var/opt/mssql/data/GalacticZoo_DR.mdf',
     MOVE 'GalacticZoo_log' TO '/var/opt/mssql/data/GalacticZoo_DR.ldf',
     NORECOVERY; 
GO