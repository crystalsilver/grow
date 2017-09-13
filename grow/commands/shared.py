"""Shared options or arguments for cli commands."""

import click


def pod_path_argument(func):
    """Argument for pod path."""
    return click.argument('pod_path', default='.')(func)


def deployment_option(func):
    """Option for deployment."""
    return click.option(
        '--deployment', default=None, help='Name of the deployment to use.')(func)
