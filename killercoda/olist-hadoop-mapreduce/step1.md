# Verificar los demonios de HDFS y YARN

```
source /etc/profile.d/hadoop.sh && cd /root/olist-dw-bigdata && . .venv/bin/activate
jps
```{{exec}}

Deben aparecer cinco procesos Java: `NameNode` y `DataNode` (HDFS), `ResourceManager` y `NodeManager` (YARN) y `JobHistoryServer`.

Capacidad de HDFS y nodos de YARN:

```
hdfs dfsadmin -report | head -15
yarn node -list -all
```{{exec}}

Abre las interfaces web desde el menú **Traffic / Ports** de Killercoda: puerto **9870** (NameNode) y **8088** (ResourceManager). Toma captura de ambas para el informe.
