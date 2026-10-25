# Copyright 2026 Joji John
# SPDX-License-Identifier: Apache-2.0
"""The `dev-charter` command."""

import click

REPOSITORY = "https://github.com/joji-opensource/charter"


@click.group(invoke_without_command=True)
@click.version_option(package_name="dev-charter", prog_name="Dev Charter")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Dev Charter: know what your product does, which code delivers it, and what is proven."""
    if ctx.invoked_subcommand is None:
        click.echo("Dev Charter is in early development and has no commands yet.")
        click.echo(f"Follow {REPOSITORY} to hear when the first release ships.")
