# Get a SQL Server running in a container

This a simple experiment to create an instance of SQL Server

## How it works

`docker-compose up -d` to start the container

Execute the scripts in order from the `./scripts` folder

`docker-compose down -v` tear it down and kill the volume

## What did we learn

Differential backups seem to be a viable option as an approach for migrating large databases when minimal downtime is needed.