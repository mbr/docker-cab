docker-cab
==========

``docker-cab`` is a small python program that waits for change notifications from
your docker daemon and regenerates an nginx configuration file each time this
happens. It autogenerates reverse-proxy entries for docker containers that are
"published".

To publish a container, three criterias must be fulfilled:

1. It must be part of the ``frontnet``-network.
2. An environment variable named `VIRTUAL_HOST` must be present.
3. An SSL certificate chain with a key must be installed (currently, SSL is
   mandatory with docker-cab, not optional).


Trying it out
-------------

You can try ``docker-cab`` right now (an automated build is available at
https://hub.docker.com/r/mbr0/docker-cab/)::

    docker run -v /var/run/docker.sock:/var/run/docker.sock --rm -it docker-cab list

Since there is most likely no ``frontnet`` network configured, the output will be
empty. See **Deploying** for a way to configure containers in a way that makes
them discoverable by ``docker-cab``.



Deploying
---------

1. Create a network named ``frontnet`` on your docker host/swarm or desktop by
   running::

    docker network create frontnet

2. Run docker-compose to start the nginx server (see
   ``cabfront/docker-compose.yml``)::

    docker-compose -d

   When testing locally, omit the ``-d`` for testing.

At this point, docker-cab is ready. If you wish to add a site with a domain
name, e.g. ``localhost``, these are the steps required:

1. Copy ``localhost.crt`` and ``localhost.key`` to
   ``/docker-volumes/cabfront-certs``. You may need `self-signed certificates
   <https://www.google.de/search?q=generate+self+signed+certificate>`_ when
   testing locally.
2. Start the app container, ensuring that it is part of the ``frontnet`` network
   and has the ``VIRTUAL_HOST`` environment variable set. Example::

     docker run --net=frontnet -e VIRTUAL_HOST=localfoo training/webapp
