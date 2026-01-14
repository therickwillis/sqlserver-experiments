# Differential Backups

This a simple experiment to create an instance of SQL Server with 2 databases.  1 database will be the primary and the other will represent a DR copy.  Will Differential backups help solve timing issues with moving large databases?

## How it works

Use the `./.env` file to change settings (like the password and port)

`docker-compose up -d` to start the container

Execute the scripts in order from the `./scripts` folder

`docker-compose down -v` tear it down and kill the volume

## What did we learn

Differential backups seem to be a viable option as an approach for migrating large databases when minimal downtime is needed.