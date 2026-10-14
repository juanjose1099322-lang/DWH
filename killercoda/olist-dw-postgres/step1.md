# Verificar PostgreSQL y la cadena de conexión

Entra al repositorio y activa el entorno de Python:

```
cd /root/olist-dw-bigdata && . .venv/bin/activate
```{{exec}}

Comprueba que el servicio escucha solo en la interfaz local (127.0.0.1:5432):

```
ss -ltnp | grep 5432
```{{exec}}

Conéctate con la cadena estándar en formato *key=value* de libpq:

```
PGPASSWORD=dw_pass psql "host=localhost port=5432 dbname=olist_dw user=dw_user" -c "SELECT current_user, current_database(), inet_server_port();"
```{{exec}}

Revisa la cadena que usará el ETL (archivo `config/.env`):

```
grep '^DW_URL' config/.env
```{{exec}}

Como cliente y servidor están en la misma máquina, no hay que abrir puertos, configurar el firewall ni usar túneles.
