{% macro upstream_proxy(fc) -%}
    proxy_redirect off;
    proxy_buffering off;
    proxy_pass http://apachephp;
    proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Scheme $scheme;
    proxy_set_header Host $host;
    proxy_read_timeout 10m;
    client_max_body_size 200M;
    proxy_pass http://{{fc.ip}}:{{fc.port}};
{%- endmacro -%}

{% for fc in fcs -%}
upstream docker_{{fc.id}} {
  server {{fc.ip}}:{{fc.port}};
}
{% endfor -%}

server {
{% for fc in fcs -%}
  {% if fc.virtual_path -%}
  # REDIRECT: {{fc.virtual_path}}
  location ~ ^{{fc.virtual_path}}(/.*)?$ {
    proxy_set_header X-Script-Name /{{fc.virtual_path}};
    {{upstream_proxy(fc)}}
  }
}

{% endif -%}
{% endfor -%}

{% for fc in fcs -%}
{% if fc.virtual_host -%}
# HTTP: {{fc.virtual_host}}
server {
  listen 80;
  server_name {{fc.virtual_host}};
  {%- if fc.ssl_enabled == "force" %}
  return 301 https://$server_name$request_uri;
  {%- else %}
  location / {
    {{upstream_proxy(fc)}}
  }
  {%- endif %}
}

{% if fc.ssl_enabled -%}
# HTTPS: {{fc.virtual_host}}
server {
  listen 443;
  server_name {{fc.virtual_host}};

  ssl_certificate           /etc/nginx/{{fc.virtual_host}}.crt;
  ssl_certificate_key       /etc/nginx/{{fc.virtual_host}}.key;

  ssl on;

  # secure configuration, see
  # https://raymii.org/s/tutorials/Strong_SSL_Security_On_nginx.html#The_BEAST_attack_and_RC4
  ssl_ciphers 'EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH';
  ssl_prefer_server_ciphers on;
  ssl_session_cache shared:SSL:10m;
}
{% endif %}
{% endif -%}
{% endfor -%}
