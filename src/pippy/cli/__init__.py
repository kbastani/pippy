# SPDX-FileCopyrightText: 2025-present kbastani <kbastani@realogicworks.com>
#
# SPDX-License-Identifier: MIT
import click

from pippy.__about__ import __version__


@click.group(context_settings={"help_option_names": ["-h", "--help"]}, invoke_without_command=True)
@click.version_option(version=__version__, prog_name="pippy")
def pippy():
    click.echo("Hello world!")
