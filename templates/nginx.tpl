{% for fc in fcs -%}
location ~ ^{{fc.virtual_path}}(/.*)?$ {
      proxy_set_header Host $host;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Scheme $scheme;
      proxy_set_header X-Script-Name /{{fc.virtual_path}};
      proxy_read_timeout 10m;
      client_max_body_size 200M;
      proxy_pass http://{{fc.ip}}:{{fc.port}};
    }
{% endfor -%}
