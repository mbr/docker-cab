{% if 'frontnet' in networks -%}
{% for id, nc in networks['frontnet']['Containers'].items()|sort -%}
{% with c = containers[id], ip = nc['IPv4Address'].split('/')[0] -%}
{% if 'WEBSITE_PATH' in c|env and c|port -%}
location ~ ^/{{(c|env)['WEBSITE_PATH']}}(/.*)?$ {
      proxy_set_header Host $host;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Scheme $scheme;
      proxy_set_header X-Script-Name /{{(c|env)['WEBSITE_PATH']}};
      proxy_read_timeout 10m;
      client_max_body_size 200M;
      proxy_pass http://{{"{}:{}".format(ip, c|port)}};
    }
{% endif -%}
{% endwith -%}
{% endfor -%}
{% endif -%}
