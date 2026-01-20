
-- Use GUIDs for seeded keys so seeds remain stable in live databases.
DECLARE @BeeVariant TABLE (ID UNIQUEIDENTIFIER, Name NVARCHAR(100), Description NVARCHAR(255), Species NVARCHAR(100));

INSERT INTO @BeeVariant (ID, Name, Description, Species) VALUES
('00000000-0000-0000-0000-000000000001', 'Stone', '', 'Hive'),
('00000000-0000-0000-0000-000000000002', 'Berry', '', 'Hive'),
('00000000-0000-0000-0000-000000000003', 'Chitin', '', 'Hive'),
('00000000-0000-0000-0000-000000000004', 'Flint', '', 'Hive'),
('00000000-0000-0000-0000-000000000005', 'Crystal', '', 'Hive'),
('00000000-0000-0000-0000-000000000006', 'Fiber', '', 'Hive'),
('00000000-0000-0000-0000-000000000007', 'Hide', '', 'Hive'),
('00000000-0000-0000-0000-000000000008', 'Metal', '', 'Hive'),
('00000000-0000-0000-0000-000000000009', 'OrganicPolymer', '', 'Hive'),
('00000000-0000-0000-0000-00000000000A', 'SpoiledMeat', '', 'Hive'),
('00000000-0000-0000-0000-00000000000B', 'Thatch', '', 'Hive'),
('00000000-0000-0000-0000-00000000000C', 'Wood', '', 'Hive'),
('00000000-0000-0000-0000-00000000000D', 'Obsidian', '', 'Hive'),
('00000000-0000-0000-0000-00000000000E', 'NarcoBerry', '', 'Hive'),
('00000000-0000-0000-0000-00000000000F', 'Narcotic', '', 'Hive'),
('00000000-0000-0000-0000-000000000010', 'SparkPowder', '', 'Hive'),
('00000000-0000-0000-0000-000000000011', 'CementingPaste', '', 'Hive'),
('00000000-0000-0000-0000-000000000012', 'Pearl', '', 'Hive'),
('00000000-0000-0000-0000-000000000013', 'Oil', '', 'Hive'),
('00000000-0000-0000-0000-000000000014', 'Sand', '', 'Hive'),
('00000000-0000-0000-0000-000000000015', 'Air', '', 'Solitary'),
('00000000-0000-0000-0000-000000000016', 'Water', '', 'Solitary'),
('00000000-0000-0000-0000-000000000017', 'Earth', '', 'Solitary'),
('00000000-0000-0000-0000-000000000018', 'Fire', '', 'Solitary'),
('00000000-0000-0000-0000-000000000019', 'Gas', '', 'Hive'),
('00000000-0000-0000-0000-00000000001A', 'Charcoal', '', 'Hive'),
('00000000-0000-0000-0000-00000000001B', 'Ingot', '', 'Hive'),
('00000000-0000-0000-0000-00000000001C', 'Carpenter', '', 'Hive'),
('00000000-0000-0000-0000-00000000001D', 'Sulfer', '', 'Hive'),
('00000000-0000-0000-0000-00000000001E', 'Cactus', '', 'Hive'),
('00000000-0000-0000-0000-00000000001F', 'Boomer', '', 'Hive'),
('00000000-0000-0000-0000-000000000020', 'Sappy', '', 'Hive'),
('00000000-0000-0000-0000-000000000021', 'Fruit', '', 'Hive'),
('00000000-0000-0000-0000-000000000022', 'Vegie', '', 'Hive'),
('00000000-0000-0000-0000-000000000023', 'Silk', '', 'Hive'),
('00000000-0000-0000-0000-000000000024', 'Pelt', '', 'Hive'),
('00000000-0000-0000-0000-000000000025', 'Mason', '', 'Hive'),
('00000000-0000-0000-0000-000000000026', 'Electric', '', 'Hive'),
('00000000-0000-0000-0000-000000000027', 'Fairy', '', 'Solitary'),
('00000000-0000-0000-0000-000000000028', 'Salty', '', 'Hive');


MERGE INTO [dbo].[BeeVariant] AS target
USING @BeeVariant AS source
ON target.Id = source.Id
WHEN MATCHED THEN
    UPDATE SET 
        Name = source.Name, 
        Description = source.Description, 
        Species = source.Species
WHEN NOT MATCHED THEN
    INSERT (Id, Name, Description, Species) VALUES (source.Id, source.Name, source.Description, source.Species);

-- This file contains SQL statements that will be executed after the build script.
