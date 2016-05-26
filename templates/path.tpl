# CFG

{% for c in containers -%}
{% if c|exposed_addr and (c|env)['SITE_PATH'] -%}
location ~ ^/{{(c|env)['SITE_PATH']}}(/.*)?$ {
      proxy_set_header Host $host;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Scheme $scheme;
      proxy_set_header X-Script-Name /{{(c|env)['SITE_PATH']}};
      proxy_read_timeout 10m;
      client_max_body_size 200M;
      proxy_pass http://{{"{}:{}".format(*c|exposed_addr)}};
    }
{% endif -%}
{% endfor -%}
