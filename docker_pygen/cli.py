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


def port(c, ptype='tcp'):
    ports = [int(port['PublicPort'])
             for port in c['Ports'] if port['Type'] == ptype and 'IP' in port]
    return sorted(ports)[0] if ports else None


env = jinja2.Environment(
    # undefined=jinja2.StrictUndefined,
    extensions=[
        'jinja2.ext.loopcontrols',
        'jinja2.ext.with_',
        'jinja2.ext.do',
    ], )


def parse_env(c):
    return dict(v.split('=', 1) for v in c['Config']['Env'])

# env.filters['public_local_ports'] = public_local_ports
env.filters['port'] = port
env.filters['env'] = parse_env


def events_listener(cl, q):
    # this *should* be threadsafe, as it is going to a different url endpoint
    for ev in cl.events():
        event = json.loads(ev.decode('ascii'))

        q.put(event)


class Table(object):
    def __init__(self, col_sizes=[], spacing=2):
        self.col_sizes = col_sizes
        self.spacing = spacing
        self.space_char = ' '

    def _join_parts(self, parts):
        return (self.space_char * self.spacing).join(parts)

    def format_row(self, *cols):
        parts = []
        for idx, col in enumerate(cols):
            size = self.col_sizes[idx]
            tx = str(col)
            parts.append(tx[:size] + self.space_char * (size - len(tx)))
        return self._join_parts(parts)

    def format_line(self, char='='):
        parts = []
        for n in self.col_sizes:
            parts.append(char * (n // len(char)))
        return self._join_parts(parts)


def exit_err(msg, status=1):
    click.echo(msg, err=1)
    sys.exit(1)


class FrontendContainer(object):
    def __init__(self, net, container):
        self.net = net
        self.container = container

    def is_publishable(self):
        return self.port and (self.virtual_host or self.virtual_path)

    @property
    def virtual_host(self):
        return self.env.get('VIRTUAL_HOST')

    @property
    def virtual_path(self):
        return self.env.get('VIRTUAL_PATH')

    @property
    def env(self):
        return parse_env(self.container)

    @property
    def id(self):
        return self.container['Id']

    @property
    def name(self):
        return self.container.get('Name') or self.id

    @property
    def ip(self):
        return self.network['IPAddress'].split('/', 1)[0]

    @property
    def addr(self):
        return self.ip, self.port

    @property
    def network(self):
        return self.container['NetworkSettings']['Networks'][self.net]

    @property
    def port(self):
        http_port = self.env.get('HTTP_PORT')

        if http_port:
            return int(http_port)

        ports = [key.split('/', 1)[0]
                 for key in self.container['NetworkSettings']['Ports'].keys()
                 if key.endswith('/tcp')]

        if ports:
            # return lowest exposted port
            return sorted(ports)[0]

        # no port found

    @classmethod
    def fetch(cls, cl, net):
        fcs = []
        for id in net['Containers'].keys():
            fcs.append(FrontendContainer(net['Name'], cl.inspect_container(
                id)))
        return fcs


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
