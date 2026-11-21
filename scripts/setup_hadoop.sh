#!/usr/bin/env bash
# ---------------------------------------------------------------------------------
# Instala Hadoop 3.3.6 en modo pseudo-distribuido (un nodo con HDFS + YARN reales)
# en Ubuntu: Killercoda, Google Colab o un PC con Ubuntu/WSL.
#
#   NameNode + DataNode            -> HDFS   (UI web http://localhost:9870)
#   ResourceManager + NodeManager  -> YARN   (UI web http://localhost:8088)
#   JobHistory Server              ->        (UI web http://localhost:19888)
#
# Todo escucha en localhost (cadena estándar local hdfs://localhost:9000), igual que
# la bodega en el Corte 2: no hay que abrir puertos ni configurar firewall.
# Uso:  sudo bash scripts/setup_hadoop.sh        (≈3-4 min, la mayor parte es la descarga)
# ---------------------------------------------------------------------------------
set -euo pipefail

HADOOP_VERSION="${HADOOP_VERSION:-3.3.6}"
export HADOOP_HOME="${HADOOP_HOME:-/opt/hadoop}"
DATA_DIR="${HADOOP_DATA:-/opt/hadoop_data}"

echo ">> [1/6] Java 11 y utilidades"
if ! java -version 2>&1 | grep -q 'version "11'; then
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq openjdk-11-jdk-headless curl python3 >/dev/null
fi
JAVA_HOME="$(dirname "$(dirname "$(readlink -f "$(command -v java)")")")"
# Si hay varias versiones de Java, se fuerza la 11 (Hadoop 3.3 no soporta Java 17+ en tiempo de ejecución)
[ -d /usr/lib/jvm/java-11-openjdk-amd64 ] && JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
export JAVA_HOME

echo ">> [2/6] Descargando Hadoop ${HADOOP_VERSION}"
if [ ! -x "${HADOOP_HOME}/bin/hadoop" ]; then
  TGZ="/tmp/hadoop-${HADOOP_VERSION}.tar.gz"
  for URL in "https://dlcdn.apache.org/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz" \
             "https://archive.apache.org/dist/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz"; do
    curl -fsSL --retry 3 -o "$TGZ" "$URL" && break
  done
  tar -xzf "$TGZ" -C /opt && rm -f "$TGZ"
  mv "/opt/hadoop-${HADOOP_VERSION}" "$HADOOP_HOME"
fi

echo ">> [3/6] Configuración pseudo-distribuida"
# Memoria para YARN: 60 % de la RAM de la máquina (mínimo 1.536 MB)
TOTAL_MB=$(free -m | awk '/Mem:/{print $2}')
YARN_MB=$(( TOTAL_MB * 6 / 10 )); [ "$YARN_MB" -lt 1536 ] && YARN_MB=1536
VCORES=$(nproc)
ETC="${HADOOP_HOME}/etc/hadoop"
mkdir -p "${DATA_DIR}"/{nn,dn,tmp}

cat > "${ETC}/core-site.xml" <<XML
<configuration>
  <property><name>fs.defaultFS</name><value>hdfs://localhost:9000</value></property>
  <property><name>hadoop.tmp.dir</name><value>${DATA_DIR}/tmp</value></property>
</configuration>
XML

# Bloques de 16 MB (por defecto 128 MB) para que los archivos del proyecto se repartan
# en varios bloques y se vean varios map tasks en paralelo, como en un clúster real.
cat > "${ETC}/hdfs-site.xml" <<XML
<configuration>
  <property><name>dfs.replication</name><value>1</value></property>
  <property><name>dfs.blocksize</name><value>16m</value></property>
  <property><name>dfs.namenode.name.dir</name><value>file://${DATA_DIR}/nn</value></property>
  <property><name>dfs.datanode.data.dir</name><value>file://${DATA_DIR}/dn</value></property>
  <property><name>dfs.permissions.enabled</name><value>false</value></property>
</configuration>
XML

cat > "${ETC}/mapred-site.xml" <<XML
<configuration>
  <property><name>mapreduce.framework.name</name><value>yarn</value></property>
  <property><name>yarn.app.mapreduce.am.env</name><value>HADOOP_MAPRED_HOME=${HADOOP_HOME}</value></property>
  <property><name>mapreduce.map.env</name><value>HADOOP_MAPRED_HOME=${HADOOP_HOME}</value></property>
  <property><name>mapreduce.reduce.env</name><value>HADOOP_MAPRED_HOME=${HADOOP_HOME}</value></property>
  <property><name>yarn.app.mapreduce.am.resource.mb</name><value>512</value></property>
  <property><name>yarn.app.mapreduce.am.command-opts</name><value>-Xmx400m</value></property>
  <property><name>mapreduce.map.memory.mb</name><value>512</value></property>
  <property><name>mapreduce.map.java.opts</name><value>-Xmx400m</value></property>
  <property><name>mapreduce.reduce.memory.mb</name><value>512</value></property>
  <property><name>mapreduce.reduce.java.opts</name><value>-Xmx400m</value></property>
  <property><name>mapreduce.jobhistory.address</name><value>localhost:10020</value></property>
  <property><name>mapreduce.jobhistory.webapp.address</name><value>localhost:19888</value></property>
</configuration>
XML

cat > "${ETC}/yarn-site.xml" <<XML
<configuration>
  <property><name>yarn.resourcemanager.hostname</name><value>localhost</value></property>
  <property><name>yarn.nodemanager.aux-services</name><value>mapreduce_shuffle</value></property>
  <property><name>yarn.nodemanager.resource.memory-mb</name><value>${YARN_MB}</value></property>
  <property><name>yarn.nodemanager.resource.cpu-vcores</name><value>${VCORES}</value></property>
  <property><name>yarn.scheduler.minimum-allocation-mb</name><value>256</value></property>
  <property><name>yarn.scheduler.maximum-allocation-mb</name><value>${YARN_MB}</value></property>
  <property><name>yarn.nodemanager.vmem-check-enabled</name><value>false</value></property>
  <property><name>yarn.nodemanager.disk-health-checker.max-disk-utilization-per-disk-percentage</name><value>98.5</value></property>
  <property><name>yarn.log-aggregation-enable</name><value>true</value></property>
  <property><name>yarn.nodemanager.env-whitelist</name>
    <value>JAVA_HOME,HADOOP_COMMON_HOME,HADOOP_HDFS_HOME,HADOOP_CONF_DIR,CLASSPATH_PREPEND_DISTCACHE,HADOOP_YARN_HOME,HADOOP_HOME,PATH,LANG,TZ,HADOOP_MAPRED_HOME</value></property>
</configuration>
XML

cat >> "${ETC}/hadoop-env.sh" <<ENV
export JAVA_HOME=${JAVA_HOME}
export HDFS_NAMENODE_USER=root HDFS_DATANODE_USER=root HDFS_SECONDARYNAMENODE_USER=root
export YARN_RESOURCEMANAGER_USER=root YARN_NODEMANAGER_USER=root
ENV

cat > /etc/profile.d/hadoop.sh <<ENV
export JAVA_HOME=${JAVA_HOME}
export HADOOP_HOME=${HADOOP_HOME}
export HADOOP_CONF_DIR=${ETC}
export PATH=\$PATH:${HADOOP_HOME}/bin:${HADOOP_HOME}/sbin
ENV
. /etc/profile.d/hadoop.sh

echo ">> [4/6] Formateando HDFS (solo la primera vez)"
[ -d "${DATA_DIR}/nn/current" ] || hdfs namenode -format -nonInteractive -force >/dev/null 2>&1

echo ">> [5/6] Iniciando demonios HDFS y YARN"
hdfs  --daemon start namenode        || true
hdfs  --daemon start datanode        || true
yarn  --daemon start resourcemanager || true
yarn  --daemon start nodemanager     || true
mapred --daemon start historyserver  || true
hdfs dfsadmin -safemode wait >/dev/null

echo ">> [6/6] Verificación"
jps | grep -v Jps
hdfs dfsadmin -report | grep -E "Live datanodes|Configured Capacity" || true
for i in $(seq 1 30); do yarn node -list 2>/dev/null | grep -q RUNNING && break; sleep 2; done
yarn node -list 2>/dev/null | tail -n +2
echo "Hadoop listo: HDFS hdfs://localhost:9000 · YARN ${YARN_MB} MB / ${VCORES} vcores"
echo "Ejecuta:  source /etc/profile.d/hadoop.sh"
