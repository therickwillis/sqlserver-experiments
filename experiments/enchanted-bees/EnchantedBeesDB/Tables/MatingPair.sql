CREATE TABLE [dbo].[MatingPair]
(
  [Id] INT NOT NULL PRIMARY KEY,
  [Variant1Id] INT NOT NULL,
  [Variant2Id] INT NOT NULL,
  FOREIGN KEY (Variant1Id) REFERENCES Variant(Id),
  FOREIGN KEY (Variant2Id) REFERENCES Variant(Id)
)
