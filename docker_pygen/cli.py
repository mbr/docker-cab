from functools import partial
import json
from queue import Queue, Empty
from threading import Thread
import sys

import click
import jinja2
from docker.client import Client

DEFAULT_URL = 'unix://var/run/docker.sock'
EVENT_TYPES = ['create', 'destroy', 'die', 'kill', 'oom', 'pause', 'restart',
               'start', 'stop', 'unpause']

info = partial(click.echo, err=True)

# helpful: https://docs.docker.com/engine/reference/api/images/event_state.png


def exposed_addr(c, ptype='tcp'):
    ports = [(port['IP'], int(port['PublicPort']))
             for port in c['Ports'] if port['Type'] == ptype and 'IP' in port]
    return ports[0] if ports else None


env = jinja2.Environment(
    # undefined=jinja2.StrictUndefined,
    extensions=[
        'jinja2.ext.loopcontrols',
        'jinja2.ext.with_',
        'jinja2.ext.do',
    ], )

# env.filters['public_local_ports'] = public_local_ports
env.filters['exposed_addr'] = exposed_addr
env.filters['env'] = lambda c: dict(v.split('=', 1)
                                    for v in c['_inspect']['Config']['Env'])


def update_configurations(cl, template, output_file, notifications):
    containers = cl.containers()
    images = cl.images()

    for container in containers:
        container['_inspect'] = cl.inspect_container(container['Id'])

    for image in images:
        image['_inspect'] = cl.inspect_image(image['Id'])

    info('Collected {} running containers and {} images'.format(
        len(containers), len(images)))

    with open(template) as tpl_src:
        tpl = env.from_string(tpl_src.read())

        info('Compiled template {}'.format(template))
        result = tpl.render(containers=containers, images=images)

    info('Successfully rendered template {}'.format(template))

    out = open(output_file, 'w') if output_file else sys.stdout
    out.write(result)

    info('Wrote {}'.format(output_file or 'to stdout'))

    # send notifications
    for signal, cid in notifications:
        info('Sending {} to {}'.format(signal, cid))
        try:
            cl.kill(cid, int(signal) if signal.isnumeric() else signal)
        except Exception as e:
            info('Error ignored: {}'.format(e))


def events_listener(cl, q):
    # this *should* be threadsafe, as it is going to a different url endpoint
    for ev in cl.events():
        event = json.loads(ev.decode('ascii'))

        q.put(event)


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
@click.option('-t',
              '--timeout',
              default=5,
              help='Seconds to wait before updating; reset after each event')
@click.option('-s',
              '--signal',
              'notifications',
              type=(str, str),
              multiple=True,
              help='Restart a container using signal. Ex: "HUP:nginx"')
@click.argument('template')
def cli(url, template, output_file, watch, events, timeout, notifications):
    # initialize Client
    cl = Client(base_url=url, version='auto')

    # output version to show the connected succeeded
    v = cl.version()
    info('Connected to Docker {v[Version]}, api version '
         '{v[ApiVersion]}.'.format(v=v))

    def do_update():
        update_configurations(cl, template, output_file, notifications)

    do_update()

    if watch:
        q = Queue()
        t = Thread(target=events_listener, args=(cl, q), daemon=True)
        t.start()

        dirty = False

        while True:
            try:
                event = q.get(block=True, timeout=timeout)
            except Empty:
                if not dirty:
                    continue

                info('Events settled after {} seconds, updating'.format(
                    timeout))
                do_update()
                dirty = False
            else:
                if not event['Type'] == 'container':
                    continue

                info('Received container event {0[Action]}'.format(event))

                if event['Action'] in EVENT_TYPES:
                    dirty = True
