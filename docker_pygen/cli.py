from functools import partial

import click
from docker.client import Client

DEFAULT_URL = 'unix://var/run/docker.sock'

info = partial(click.echo, err=True)

# helpful: https://docs.docker.com/engine/reference/api/images/event_state.png


def update_configurations(cl, events=[]):
    containers = cl.containers(all=True)
    images = cl.images()
    container_details = {id: cl.inspect_container(c['Id']) for c in containers}
    images_details = {id: cl.inspect_image(i['Id']) for i in images}

    info('Collected {} running containers and {} images'.format(
        len(containers), len(images)))


@click.command('docker-pygen')
@click.option('-u',
              '--url',
              default=DEFAULT_URL,
              help='The url used to connect ot the docker server [default: ' +
              DEFAULT_URL + ']')
def cli(url):
    # initialize Client
    cl = Client(base_url=url, version='auto')

    # output version to show the connected succeeded
    v = cl.version()
    info('Connected to Docker {v[Version]}, api version '
         '{v[ApiVersion]}.'.format(v=v))

    update_configurations(cl)
