# Operaciones OLAP y versionamiento

Ejecuta las 5 operaciones (roll-up, drill-down, slice, dice, pivot) y las consultas de las preguntas de negocio:

```
python etl/ejecutar_sql.py sql/03_operaciones_olap.sql
```{{exec}}

Deja constancia en Git del laboratorio ejecutado (el log no se versiona; el resultado sí):

```
mkdir -p evidencias && python etl/ejecutar_sql.py sql/03_operaciones_olap.sql > evidencias/killercoda_operaciones.txt
git add evidencias/ && git -c user.name="Equipo DW" -c user.email="equipo@example.com" commit -m "Evidencia: operaciones OLAP en PostgreSQL (Killercoda)"
git log --oneline -3
```{{exec}}

Para subir la evidencia a GitHub necesitas un token personal: `git push https://<token>@github.com/juanjose1099322-lang/DWH.git main`.
