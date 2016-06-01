docker-cab
==========

An auto-discovering load-balancer/reverse-proxy configurator for docker. Work
in progress.

Trying it out
-------------

You can try `docker-cab` right now by using the provided docker image and
running:

    docker run -v /var/run/docker.sock:/var/run/docker.sock --rm -it docker-cab list

Since there is most likely no `frontnet` network configured, the output will be
empty. See deploying for a way to configure containers in a way that makes the
discoverable by `docker-cab`.



Deploying
---------

1. Create a network named `frontnet` on your docker host/swarm by running::

    docker network create frontnet

2. Run docker-compose to start the nginx server (see
   `cabfront/docker-compose.yml`)::

    docker-compose -d
