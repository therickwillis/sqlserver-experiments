CREATE TABLE [dbo].[MatingBaby]
(
  [Id] INT NOT NULL PRIMARY KEY,
  [MatingPairId] INT NOT NULL,
  [BabyVariantId] INT NOT NULL,
  FOREIGN KEY (MatingPairId) REFERENCES MatingPair(Id),
  FOREIGN KEY (BabyVariantId) REFERENCES Variant(Id)
)
