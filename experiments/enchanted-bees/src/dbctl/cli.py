#!/usr/bin/env python3
"""
dbctl CLI - Main entry point for database management commands
"""

import click
import os
import sys
from pathlib import Path


@click.group()
@click.version_option(version="0.1.0")
@click.pass_context
def cli(ctx):
    """
    dbctl - Database Management CLI

    Manage MSSQL databases through containerized operations.
    Works identically on Windows, Mac, and Linux.
    """
    ctx.ensure_object(dict)

    # Set workspace root
    ctx.obj['WORKSPACE_ROOT'] = Path('/workspace')


@cli.command()
@click.option('--project', '-p', default='EnchantedBeesDB/EnchantedBeesDB.sqlproj',
              help='Path to SQL project file relative to workspace')
@click.option('--configuration', '-c', default='Debug',
              help='Build configuration (Debug/Release)')
@click.pass_context
def build(ctx, project, configuration):
    """Build SQL project and generate DACPAC"""
    from .commands import build_command
    build_command.build(ctx, project, configuration)


@cli.command()
@click.pass_context
def status(ctx):
    """Show database and migration status"""
    from .commands import status_command
    status_command.status(ctx)


@cli.command()
@click.pass_context
def info(ctx):
    """Show environment and tooling information"""
    from .commands import info_command
    info_command.info(ctx)


def main():
    """Entry point for the CLI"""
    cli(obj={})


if __name__ == '__main__':
    main()
