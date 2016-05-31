# FIXME: we should support multiple instances and pooling here
#        possibly adding a pool id for load-balancing?


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
        return dict(v.split('=', 1) for v in self.container['Config']['Env'])

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

    @property
    def ssl_enabled(self):
        """One of False, True, 'force'"""
        return True

    @classmethod
    def fetch(cls, cl, net):
        fcs = []
        for id in net['Containers'].keys():
            fcs.append(FrontendContainer(net['Name'], cl.inspect_container(
                id)))
        return fcs
