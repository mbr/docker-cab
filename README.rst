docker-cab
==========

An auto-discovering load-balancer/reverse-proxy configurator for docker. Work
in progress.


How to
------

1. Create a network named `frontnet` on your docker host/swarm by running::

    docker network create frontnet

2. Run docker-compose to start the nginx server (see
   `cabfront/docker-compose.yml`)::

    docker-compose -d
