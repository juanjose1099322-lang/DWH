#!/usr/bin/env bash
# ---------------------------------------------------------------------------------
# Ejecuta el pipeline MapReduce del Corte 3 en Hadoop (HDFS + YARN) y guarda las
# evidencias de cada paso en evidencias/ (se versionan en GitHub).
#
#   1. HDFS: crea directorios, sube los insumos, lista bloques (carga y escritura)
#   2. YARN: lanza 6 jobs Hadoop Streaming con los mismos mappers/reducers en Python
#   3. HDFS: lee las salidas (cat / getmerge) y las deja en data/mr_out/
#   4. YARN: guarda la lista de aplicaciones, métricas del clúster y contadores
#
# Requisitos: scripts/setup_hadoop.sh ejecutado y mapreduce/preparar_insumos.py corrido.
# Uso:  bash mapreduce/run_hadoop.sh
# ---------------------------------------------------------------------------------
set -euo pipefail
. /etc/profile.d/hadoop.sh 2>/dev/null || true

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
MR=mapreduce
IN=data/hdfs_in
OUT=data/mr_out
EV=evidencias
HDFS_RAW=/olist/raw
HDFS_MR=/olist/mr
STREAMING=$(ls "${HADOOP_HOME}"/share/hadoop/tools/lib/hadoop-streaming-*.jar)
mkdir -p "$OUT" "$EV"
: > "$EV/tiempos_yarn.tsv"

seccion() { echo; echo "=================== $* ==================="; }
# Nota: "cmd | head" cierra la tubería antes de tiempo y el comando de la izquierda
# termina con error (SIGPIPE). Por eso esas líneas llevan "|| true": solo muestran muestras.

# ---------------------------------------------------------------- 1. HDFS: carga
{
  seccion "Estado del clúster"
  jps | grep -v Jps
  hdfs dfsadmin -report | head -20 || true
  yarn node -list -all

  seccion "Carga a HDFS"
  hdfs dfs -mkdir -p "$HDFS_RAW" "$HDFS_MR"
  hdfs dfs -put -f "$IN/resenas.tsv" "$IN/entregas.tsv" "$IN/geolocalizacion.csv" "$HDFS_RAW/"
  hdfs dfs -ls -h "$HDFS_RAW"
  hdfs dfs -du -s -h "$HDFS_RAW"

  seccion "Bloques y réplicas (fsck)"
  hdfs fsck "$HDFS_RAW/geolocalizacion.csv" -files -blocks -locations | head -25 || true

  seccion "Lectura de muestra desde HDFS"
  hdfs dfs -cat "$HDFS_RAW/resenas.tsv" | head -3 || true
  hdfs dfs -tail "$HDFS_RAW/entregas.tsv" | tail -2 || true
} 2>&1 | tee "$EV/01_hdfs_carga.log"

# ---------------------------------------------------------------- 2. YARN: jobs
# lanzar <nombre> <entradas> <mapper> <reducer> [combiner] [archivos extra para -files]
# Nota: las opciones genéricas (-D, -files) deben ir antes que las de streaming.
lanzar() {
  local nombre=$1 entradas=$2 mapper=$3 reducer=$4 combiner=${5:-} extra=${6:-}
  local files="$MR/texto_pt.py,$MR/${reducer%% *}"
  [ "$mapper" != "cat" ] && files="$files,$MR/${mapper%% *}"
  [ -n "$extra" ] && files="$files,$extra"
  local args=(-D mapreduce.job.name="olist-$nombre" -D mapreduce.job.reduces=2
              -files "$files" -cmdenv PYTHONIOENCODING=utf-8 -input "$entradas" -output "$HDFS_MR/$nombre"
              -reducer "python3 $reducer")
  if [ "$mapper" = "cat" ]; then args+=(-mapper cat); else args+=(-mapper "python3 $mapper"); fi
  [ -n "$combiner" ] && args+=(-combiner "python3 $combiner")
  hdfs dfs -rm -r -f -skipTrash "$HDFS_MR/$nombre" >/dev/null 2>&1 || true
  local t0=$(date +%s)
  hadoop jar "$STREAMING" "${args[@]}" 2>&1 | tee "$EV/job_${nombre}.log"
  local t1=$(date +%s)
  local appid=$(grep -o 'application_[0-9_]*' "$EV/job_${nombre}.log" | head -1)
  printf "%s\t%s\t%s\n" "$nombre" "$appid" "$((t1 - t0))" >> "$EV/tiempos_yarn.tsv"
  hdfs dfs -getmerge "$HDFS_MR/$nombre" "/tmp/$nombre.tsv"
  rm -rf "$OUT/$nombre" && mkdir -p "$OUT/$nombre"
  mv "/tmp/$nombre.tsv" "$OUT/$nombre/part-00000" && touch "$OUT/$nombre/_SUCCESS"
}

lanzar job1_terminos    "$HDFS_RAW/resenas.tsv" job1_mapper.py job1_reducer.py "job1_reducer.py --combiner"
cp "$OUT/job1_terminos/part-00000" "$MR/modelo_nb.tsv"
lanzar job2a_join       "$HDFS_RAW/resenas.tsv,$HDFS_RAW/entregas.tsv" job2_mapper.py job2_reducer.py
lanzar job2b_temas      "$HDFS_MR/job2a_join" cat job2b_reducer.py
lanzar job3a_centroides "$HDFS_RAW/geolocalizacion.csv" job3a_mapper.py job3a_reducer.py "job3a_reducer.py --combiner"
cp "$OUT/job3a_centroides/part-00000" "$MR/centroides.tsv"
lanzar job3b_distancias "$HDFS_RAW/entregas.tsv" job3b_mapper.py job3b_reducer.py "job3b_reducer.py --combiner" "$MR/centroides.tsv"
lanzar job4_clasificar  "$HDFS_RAW/resenas.tsv" job4_mapper.py job4_reducer.py "" "$MR/modelo_nb.tsv"
rm -f "$MR/modelo_nb.tsv" "$MR/centroides.tsv"

# ---------------------------------------------------------------- 3 y 4. Lectura y YARN
{
  seccion "Salidas en HDFS"
  hdfs dfs -ls -R "$HDFS_MR" | grep -E "part-|_SUCCESS"
  seccion "Lectura de resultados (hdfs dfs -cat)"
  hdfs dfs -cat "$HDFS_MR/job2b_temas/part-*"
  hdfs dfs -cat "$HDFS_MR/job3b_distancias/part-*" | grep -v RUTA
  seccion "Aplicaciones YARN"
  yarn application -list -appStates FINISHED,FAILED,KILLED
  seccion "Métricas del ResourceManager (REST)"
  curl -s http://localhost:8088/ws/v1/cluster/metrics; echo
  seccion "Tiempos por job (s)"
  cat "$EV/tiempos_yarn.tsv"
} 2>&1 | tee "$EV/02_hdfs_yarn_resultados.log"

curl -s "http://localhost:8088/ws/v1/cluster/apps?states=FINISHED" > "$EV/yarn_apps.json" || true
python3 "$MR/verificar_salidas.py" | tee "$EV/03_verificacion.log"
echo "Listo. Salidas en $OUT/ · evidencias en $EV/"
