from functools import partial
import sys

import click
import jinja2
from docker.client import Client

DEFAULT_URL = 'unix://var/run/docker.sock'

info = partial(click.echo, err=True)

# helpful: https://docs.docker.com/engine/reference/api/images/event_state.png


def public_local_ports(container, type='tcp'):
    ports = []
    for port in container['Ports']:
        if port.get('Type') != type:
            continue

        if 'PublicPort' in port and port.get('IP') == '127.0.0.1':
            ports.append(port['PublicPort'])

    return ports


def name_and_port(container):
    names = container.get('Names', [])

    if not names:
        info('Skipping container {}, has no name'.format(container['Id']))
        return None

    ports = public_local_ports(container)
    if not ports:
        info('Skipping container {}, has no exposted ports bound to '
             '127.0.0.1'.format(container['Id']))
        return None

    return names[0], sorted(ports)[0]


env = jinja2.Environment(undefined=jinja2.StrictUndefined,
                         extensions=[
                             'jinja2.ext.loopcontrols',
                             'jinja2.ext.with_',
                             'jinja2.ext.do',
                         ], )
env.filters['public_local_ports'] = public_local_ports
env.filters['name_and_port'] = name_and_port


def update_configurations(cl, template, output_file, events=[]):
    containers = cl.containers(all=True)
    images = cl.images()
    container_details = {id: cl.inspect_container(c['Id']) for c in containers}
    image_details = {id: cl.inspect_image(i['Id']) for i in images}

    info('Collected {} running containers and {} images'.format(
        len(containers), len(images)))

    with open(template) as tpl_src:
        tpl = env.from_string(tpl_src.read())

        info('Compiled template {}'.format(template))
        result = tpl.render(containers=containers,
                            images=images,
                            container_details=container_details,
                            image_details=image_details)

    info('Successfully rendered template {}'.format(template))

    outp = open(output_file, 'w') if output_file else sys.stdout

    with outp as out:
        out.write(result)

    info('Wrote {}'.format(output_file or 'to stdout'))


@click.command('docker-pygen')
@click.option('-u',
              '--url',
              default=DEFAULT_URL,
              help='The url used to connect to the docker server [default: ' +
              DEFAULT_URL + ']')
@click.option('-o',
              '--output-file',
              help='Output directory for template files',
              type=click.Path())
@click.option('-w',
              '--watch',
              is_flag=True,
              default=False,
              help='Wait for events and rerun after each change')
@click.argument('template')
def cli(url, template, output_file, watch):
    # initialize Client
    cl = Client(base_url=url, version='auto')

    # output version to show the connected succeeded
    v = cl.version()
    info('Connected to Docker {v[Version]}, api version '
         '{v[ApiVersion]}.'.format(v=v))

    update_configurations(cl, template, output_file)
    if watch:
        for ev in cl.events():
            info('Received event: {}'.format(ev))
            pass
