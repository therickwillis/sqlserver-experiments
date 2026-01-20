-- This file contains SQL statements that will be executed after the build script.

-- Use GUIDs for seeded keys so seeds remain stable in live databases.
DECLARE @Species TABLE (Id UNIQUEIDENTIFIER, Name NVARCHAR(100), Description NVARCHAR(255));

INSERT INTO @Species (Id, Name, Description) VALUES
('00000000-0000-0000-0000-000000000001', 'Hive', 'A bee that makes a hive that produces resources.'),
('00000000-0000-0000-0000-000000000002', 'Solitary', 'A bee that wanders the world and joins you on your shoulder.');

MERGE INTO [dbo].[SpeciesType] AS target
USING @Species AS source
ON target.Id = source.Id
WHEN MATCHED THEN
    UPDATE SET Name = source.Name, Description = source.Description
WHEN NOT MATCHED THEN
    INSERT (Id, Name, Description) VALUES (source.Id, source.Name, source.Description);

