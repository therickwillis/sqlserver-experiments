-- This file contains SQL statements that will be executed after the build script.

DECLARE @Species TABLE (Id INT, Name NVARCHAR(100), Description NVARCHAR(255));

INSERT INTO @Species (Id, Name, Description) VALUES
(1, 'Hive', 'A bee that makes a hive that produces resources.'),
(2, 'Solitary', 'A bee that wanders the world and joins you on your shoulder.');

MERGE INTO [dbo].[Species] AS target
USING @Species AS source
ON target.Id = source.Id
WHEN MATCHED THEN
    UPDATE SET Name = source.Name, Description = source.Description
WHEN NOT MATCHED THEN
    INSERT (Id, Name, Description) VALUES (source.Id, source.Name, source.Description);

