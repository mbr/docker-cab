from functools import partial
import json
from queue import Queue, Empty
from threading import Thread
import sys

import click
import jinja2
from docker.client import Client

from .frontend_container import FrontendContainer
from .util import Table, exit_err

DEFAULT_URL = 'unix://var/run/docker.sock'
EVENT_TYPES = ['create', 'destroy', 'die', 'oom', 'pause', 'restart', 'start',
               'stop', 'unpause']

info = partial(click.echo, err=True)

# helpful: https://docs.docker.com/engine/reference/api/images/event_state.png

env = jinja2.Environment(
    # undefined=jinja2.StrictUndefined,
    extensions=[
        'jinja2.ext.loopcontrols',
        'jinja2.ext.with_',
        'jinja2.ext.do',
    ], )


def events_listener(cl, q):
    # this *should* be threadsafe, as it is going to a different url endpoint
    for ev in cl.events():
        event = json.loads(ev.decode('ascii'))

        q.put(event)


@click.group()
@click.option('-u',
              '--url',
              default=DEFAULT_URL,
              help='The url used to connect to the docker server [default: ' +
              DEFAULT_URL + ']')
@click.option('-n',
              '--network',
              default='frontnet',
              help='Frontend network name', )
@click.pass_context
def cli(ctx, url, network):
    # initialize Client
    cl = Client(base_url=url, version='auto')

    # output version to show the connected succeeded
    v = cl.version()
    info('Connected to Docker {v[Version]}, api version '
         '{v[ApiVersion]}.'.format(v=v))

    # find frontend network
    nets = [n for n in cl.networks(names=[network]) if n['Name'] == network]

    assert len(nets) < 2  # WTF?

    if not nets:
        exit_err("Could not find a network name {!r}".format(network))

    ctx.obj = {'cl': cl, 'network_name': network, 'network': nets[0]}


@cli.command()
@click.pass_obj
def list(obj):
    fcs = FrontendContainer.fetch(obj['cl'], obj['network'])

    tbl = Table([20, 15, 5, 18, 18])
    info(tbl.format_row('Container',
                        'IP',
                        'Port',
                        'Virtual Host',
                        'Virtual Path', ))
    info(tbl.format_line())

    for fc in sorted(fcs, key=lambda fc: fc.name):
        col = 'green' if fc.is_publishable() else 'red'

        info(click.style(
            tbl.format_row(fc.name,
                           fc.ip,
                           fc.port,
                           fc.virtual_host,
                           fc.virtual_path, ),
            fg=col))


@cli.command()
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
@click.pass_obj
def generate(obj, template, output_file, watch, timeout, notifications):
    cl = obj['cl']

    if watch:
        q = Queue()
        t = Thread(target=events_listener, args=(cl, q), daemon=True)
        t.start()

        dirty = False

    while True:
        fcs = FrontendContainer.fetch(obj['cl'], obj['network'])

        with open(template) as tpl_src:
            tpl = env.from_string(tpl_src.read())

            result = tpl.render(fcs=[fc for fc in fcs if fc.is_publishable()])

        info('Successfully rendered template {}'.format(template))

        if output_file:
            with open(output_file, 'w') as out:
                out.write(result)
        else:
            sys.stdout.write(result)

        info('Wrote {}'.format(output_file or 'to stdout'))

        # send notifications
        for signal, cid in notifications:
            info('Sending {} to {}'.format(signal, cid))
            try:
                cl.kill(cid, int(signal) if signal.isnumeric() else signal)
            except Exception as e:
                info('Error ignored: {}'.format(e))

        if not watch:
            # exit, we're done!
            sys.exit(0)

        while True:
            try:
                event = q.get(block=True, timeout=timeout)
            except Empty:
                if not dirty:
                    continue

                info('Events settled after {} seconds, updating'.format(
                    timeout))
                dirty = False
            else:
                if not event['Type'] == 'container':
                    continue

                info('Received container event {0[Action]}'.format(event))

                if event['Action'] in EVENT_TYPES:
                    dirty = True
