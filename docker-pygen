#!/usr/bin/python

import argparse
from datetime import datetime
from docker import Client
from logging import basicConfig, info, INFO
import json
import subprocess

basicConfig(format='%(asctime)-15s %(message)s', level=INFO)

TRIGGERING_EVENTS = ['create', 'destroy', 'die', 'kill', 'oom', 'pause',
                     'restart', 'start', 'stop', 'unpause']
TAG_NAME = 'com.github.mbr.app_name'
TAG_PORT = 'com.github.mbr.app_http_port'

parser = argparse.ArgumentParser()
parser.add_argument('-C',
                    '--nginx-conf',
                    default='/etc/nginx/nginx-docker.conf')
parser.add_argument('-w', '--watch', action='store_true')


def update_conf(client, conf):
    mappings = []

    for cont in client.containers():
        port = cont['Labels'].get(TAG_PORT, None)
        if port:
            port = int(port)

            for p in cont['Ports']:
                if p['PrivatePort'] == port:
                    if not 'PublicPort' in p:
                        info('Private port not exposed, skipping...')
                        continue

                    cport = p['PublicPort']

                    # determine name
                    name = cont['Labels'].get(TAG_NAME)

                    if not name and cont['Names']:
                        # if no label present, use container name
                        name = cont['Names'][0].strip('/')

                    if name:
                        mappings.append({'name': name, 'port': cport, })

    with open(conf, 'w') as out:
        for m in mappings:
            out.write("""location ~ ^/{name}(/.*)?$ {{
      proxy_set_header Host $host;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Scheme $scheme;
      proxy_set_header X-Script-Name /{name};
      proxy_read_timeout 10m;
      client_max_body_size 200M;
      proxy_pass http://localhost:{port};
    }}
""".format(**m))

    info('new nginx config fragment: {!r}'.format(sorted(m['name']
                                                         for m in mappings)))

    # reload nginx
    subprocess.check_call(['systemctl', 'reload', 'nginx'])
    info('reloaded nginx')


if __name__ == '__main__':
    args = parser.parse_args()
    client = Client()

    update_conf(client, args.nginx_conf)

    if args.watch:
        for ev in client.events():
            event = json.loads(ev)
            if event['status'] in TRIGGERING_EVENTS:
                ts = datetime.fromtimestamp(event['time'])
                event['ts'] = ts
                event['name'] = event['id'][:12]

                info('{status} {name}'.format(**event))
                update_conf(client, args.nginx_conf)
