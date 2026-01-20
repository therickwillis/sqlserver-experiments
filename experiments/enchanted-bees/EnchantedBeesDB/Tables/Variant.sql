CREATE TABLE [dbo].[Variant]
(
  [Id] INT NOT NULL PRIMARY KEY,
  [Name] NVARCHAR(100) NOT NULL,
  [Description] NVARCHAR(255) NULL,
  [SpeciesId] INT NOT NULL,
  FOREIGN KEY (SpeciesId) REFERENCES [dbo].[Species](Id)
)
