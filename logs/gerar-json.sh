#!/bin/bash
# Converte um arquivo nfcapd em JSON (saida do nfdump) para teste local.
# Uso: ./gerar-json.sh [arquivo_nfcapd] [saida_json]

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
ENTRADA="${1:-$DIR/nfcapd.202606142225}"
SAIDA="${2:-$DIR/flows.json}"

if [ ! -f "$ENTRADA" ]; then
  echo "Arquivo nao encontrado: $ENTRADA"
  exit 1
fi

nfdump -r "$ENTRADA" -o json > "$SAIDA"

echo "JSON gerado em: $SAIDA"
echo "Agora rode a API com:"
echo "  PLOG_FLOW_LOCAL_PATH=\"$SAIDA\" uvicorn main:app --reload --host 127.0.0.1 --port 8000"
