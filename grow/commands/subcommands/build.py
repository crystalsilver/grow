"""Command for building pods into static deployments."""

import os
import click
from grow.commands import shared
from grow.common import utils
from grow.deployments import stats
from grow.deployments.destinations import local as local_destination
from grow.pods import pods
from grow.pods import storage
from grow.rendering import renderer


# pylint: disable=too-many-locals
@click.command()
@shared.pod_path_argument
@click.option('--out_dir', '--out-dir', help='Where to output built files.')
@click.option('--preprocess/--no-preprocess', '-p/-np',
              default=True, is_flag=True,
              help='Whether to run preprocessors.')
@click.option('--clear-cache',
              default=False, is_flag=True,
              help='Clear the pod cache before building.')
@click.option('--file', '--pod-path', 'pod_paths',
              help='Build only pages affected by content files.', multiple=True)
@click.option('--locate-untranslated',
              default=False, is_flag=True,
              help='Shows untranslated message information.')
@shared.deployment_option
@shared.reroute_option
def build(pod_path, out_dir, preprocess, clear_cache, pod_paths,
          locate_untranslated, deployment, use_reroute):
    """Generates static files and dumps them to a local destination."""
    root = os.path.abspath(os.path.join(os.getcwd(), pod_path))
    out_dir = out_dir or os.path.join(root, 'build')

    pod = pods.Pod(root, storage=storage.FileStorage, use_reroute=use_reroute)
    if not pod_paths or clear_cache:
        # Clear the cache when building all, only force if the flag is used.
        pod.podcache.reset(force=clear_cache)
    if deployment:
        deployment_obj = pod.get_deployment(deployment)
        pod.set_env(deployment_obj.config.env)
    if preprocess:
        with pod.profile.timer('grow_preprocess'):
            pod.preprocess()
    if locate_untranslated:
        pod.enable(pod.FEATURE_TRANSLATION_STATS)
    try:
        with pod.profile.timer('grow_build'):
            config = local_destination.Config(out_dir=out_dir)
            destination = local_destination.LocalDestination(config)
            destination.pod = pod
            repo = utils.get_git_repo(pod.root)
            if use_reroute:
                pod.router.use_simple()
                if pod_paths:
                    pod.router.add_pod_paths(pod_paths)
                else:
                    pod.router.add_all()
                routes = pod.router.routes
                stats_obj = stats.Stats(pod, paths=routes.paths)
                rendered_docs = renderer.Renderer.rendered_docs(pod, routes)
                destination.deploy(
                    rendered_docs, stats=stats_obj, repo=repo,
                    confirm=False, test=False, is_partial=bool(pod_paths))
            else:
                paths, _ = pod.determine_paths_to_build(pod_paths=pod_paths)
                stats_obj = stats.Stats(pod, paths=paths)
                content_generator = destination.dump(pod, pod_paths=pod_paths)
                destination.deploy(
                    content_generator, stats=stats_obj, repo=repo, confirm=False,
                    test=False, is_partial=bool(pod_paths))

            pod.podcache.write()
    except pods.Error as err:
        raise click.ClickException(str(err))
    if locate_untranslated:
        pod.translation_stats.pretty_print()
        destination.export_untranslated_catalogs()
    return pod
