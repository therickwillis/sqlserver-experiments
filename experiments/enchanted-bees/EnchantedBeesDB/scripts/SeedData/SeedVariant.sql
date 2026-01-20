
DECLARE @Variant TABLE (ID INT, Name NVARCHAR(100), Description NVARCHAR(255), SpeciesId INT);

INSERT INTO @Variant (ID, Name, Description, SpeciesId) VALUES
(1, 'Stone', '', 1),
(2, 'Berry', '', 1),
(3, 'Chitin', '', 1),
(4, 'Flint', '', 1),
(5, 'Crystal', '', 1),
(6, 'Fiber', '', 1),
(7, 'Hide', '', 1),
(8, 'Metal', '', 1),
(9, 'OrganicPolymer', '', 1),
(10, 'SpoiledMeat', '', 1),
(11, 'Thatch', '', 1),
(12, 'Wood', '', 1),
(13, 'Obsidian', '', 1),
(14, 'NarcoBerry', '', 1),
(15, 'Narcotic', '', 1),
(16, 'SparkPowder', '', 1),
(17, 'CementingPaste', '', 1),
(18, 'Pearl', '', 1),
(19, 'Oil', '', 1),
(20, 'Sand', '', 1),
(21, 'Air', '', 2),
(22, 'Water', '', 2),
(23, 'Earth', '', 2),
(24, 'Fire', '', 2),
(25, 'Gas', '', 1),
(26, 'Charcoal', '', 1),
(27, 'Ingot', '', 1),
(28, 'Carpenter', '', 1),
(29, 'Sulfer', '', 1),
(30, 'Cactus', '', 1),
(31, 'Boomer', '', 1),
(32, 'Sappy', '', 1),
(33, 'Fruit', '', 1),
(34, 'Vegie', '', 1),
(35, 'Silk', '', 1),
(36, 'Pelt', '', 1),
(37, 'Mason', '', 1),
(38, 'Electric', '', 1),
(39, 'Fairy', '', 2),
(40, 'Salty', '', 1);


MERGE INTO [dbo].[Variant] AS target
USING @Variant AS source
ON target.Id = source.Id
WHEN MATCHED THEN
    UPDATE SET 
        Name = source.Name, 
        Description = source.Description, 
        SpeciesId = source.SpeciesId
WHEN NOT MATCHED THEN
    INSERT (Id, Name, Description, SpeciesId) VALUES (source.Id, source.Name, source.Description, source.SpeciesId);

-- This file contains SQL statements that will be executed after the build script.
