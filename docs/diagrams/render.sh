#!/bin/bash
# 渲染所有 PlantUML 类图为 PNG
# 依赖：Java 11+（已安装），Graphviz（可选，已用 smetana 代替）
# 用法：bash render.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JAR="$SCRIPT_DIR/plantuml.jar"

if [ ! -f "$JAR" ]; then
  echo "[ERROR] plantuml.jar not found at $JAR"
  exit 1
fi

echo "[INFO] Rendering PlantUML diagrams..."
java -jar "$JAR" -charset UTF-8 -png "$SCRIPT_DIR"/*.puml

if [ $? -eq 0 ]; then
  echo "[OK] All PNG files generated:"
  ls -lh "$SCRIPT_DIR"/*.png
else
  echo "[ERROR] Rendering failed, check output above."
fi
