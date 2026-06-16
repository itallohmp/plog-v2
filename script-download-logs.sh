#!/bin/bash

# PARAMETROS RECEBIDOS NA EXECUCAO  ###############################################################

route="${1:-rj02bd01}"
ano="$2"
mes="$3"
dia="$4"
remote_host="${FLOW_REMOTE_HOST:-10.10.10.53}"
remote_user="${FLOW_REMOTE_USER:-plog}"
remote_dir="${FLOW_REMOTE_DIR:-/var/flows/$route}"
local_dir="${FLOW_CACHE_DIR:-/home/plog/venv/logs/flows/$route}/$ano/$mes/$dia"

datahoraatual=$(date '+%Y-%m-%d %H:%M:%S')
echo "SCRIPT CONEXAO EXECUTADO $datahoraatual" >> /home/plog/venv/logs/logscriptconect.txt

#####################################################################################################


# VALIDA PARAMETROS E CREDENCIAL ####################################################################
if [ -z "$ano" ] || [ -z "$mes" ] || [ -z "$dia" ]; then
  echo "Uso: $0 [rota] ano mes dia"
  exit 2
fi

if [ -z "$PLOG_FLOW_SFTP_PASSWORD" ]; then
  echo "Variavel PLOG_FLOW_SFTP_PASSWORD nao configurada"
  exit 2
fi
#####################################################################################################


# VALIDA SE JSON JA EXISTE PARA EVITAR NOVO DOWNLOAD ################################################
if ls "$local_dir"/*.json >/dev/null 2>&1; then
  echo "Arquivo JSON existente"
  exit 0
else
  echo "Arquivo JSON nao existe, continuar para download"
fi
#####################################################################################################


# CRIA DIRETORI0 PARA ALOCAR O ARQUIVO QUE SERA ANALISADO  ##########################################
mkdir -p "$local_dir"
cd "$local_dir" || exit 1
#########################################################

# CONECTA NO SERVIDOR DE FLOW E BAIXA JSON PARA A PASTA CRIADA ACIMA ###############################
export SSHPASS="$PLOG_FLOW_SFTP_PASSWORD"
sshpass -e sftp -o BatchMode=no -o PubkeyAuthentication=no -b - "$remote_user@$remote_host" <<EOF
cd $remote_dir
ls
mget *$ano-$mes-$dia*.json
mget *$ano$mes$dia*.json
EOF
#####################################################################################################

if ! ls "$local_dir"/*.json >/dev/null 2>&1; then
  echo "Nenhum JSON encontrado para $ano-$mes-$dia em $remote_dir"
  exit 1
fi
