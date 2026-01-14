/*
  Topic: Galactic Zoo & Sanctuary
  Description: Tracks alien species, their habitats, and their keepers.
*/

-- 1. Create the Database
CREATE DATABASE GalacticZoo;
GO
USE GalacticZoo;
GO

-- 2. Create Tables
CREATE TABLE Exhibits (
    ExhibitID INT PRIMARY KEY IDENTITY(1,1),
    Name NVARCHAR(50) NOT NULL,
    ClimateType NVARCHAR(50),
    Capacity INT
);

CREATE TABLE Zookeepers (
    KeeperID INT PRIMARY KEY IDENTITY(1,1),
    FirstName NVARCHAR(50),
    LastName NVARCHAR(50),
    Specialization NVARCHAR(50)
);

CREATE TABLE Species (
    SpeciesID INT PRIMARY KEY IDENTITY(1,1),
    CommonName NVARCHAR(50) NOT NULL,
    HomePlanet NVARCHAR(50),
    DietType NVARCHAR(20), -- Herbivore, Carnivore, Omnivore, Radiovore
    ExhibitID INT FOREIGN KEY REFERENCES Exhibits(ExhibitID),
    LeadKeeperID INT FOREIGN KEY REFERENCES Zookeepers(KeeperID)
);

-- 3. Insert Sample Data
INSERT INTO Exhibits (Name, ClimateType, Capacity) VALUES 
('Nebula Mist Basin', 'High Humidity', 5),
('Magma Flats', 'Extreme Heat', 3),
('Zero-G Aviary', 'Vacuum/No Gravity', 10),
('Crystal Tundra', 'Sub-Zero', 4);

INSERT INTO Zookeepers (FirstName, LastName, Specialization) VALUES 
('Zorg', 'Blaster', 'Apex Predators'),
('Luna', 'Starweaver', 'Telepathic Creatures'),
('Krel', 'Vane', 'Invertebrates');

INSERT INTO Species (CommonName, HomePlanet, DietType, ExhibitID, LeadKeeperID) VALUES 
('Glow-Whale', 'Oceanus Prime', 'Plankton', 1, 2),
('Magma Newt', 'Mustafar Delta', 'Lava Rocks', 2, 1),
('Void Hawk', 'The Great Nothing', 'Starlight', 3, 1),
('Crystal Fox', 'Hoth II', 'Omnivore', 4, 3),
('Tele-Hamster', 'Mind Palace', 'Seeds/Thoughts', 1, 2);