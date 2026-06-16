#!/bin/bash
# PARAMETROS RECEBIDOS NA EXCECUCAO  ###############################################################

host="$1"
ano="$2"
mes="$3"
dia="$4"

datahoraatual=$(date '+%Y-%m-%d %H:%M:%S')
echo "SCRIPT DESCOMPACTA EXECUTADO $datahoraatual" >> /home/plog/venv/logs/logscriptdescompacta.txt

#####################################################################################################

# VALIDA SE JA EXISTE ###############################################################################
if [ -f /home/plog/venv/logs/$host/$ano/$mes/$dia/23.log ]; then
  echo "Arquivo ja descompactado"
exit
else
  echo "Arquivo Nao existe, necessario descompactar"
fi
#####################################################################################################


# DESCOMPACTAR ######################################################################################
cd /home/plog/venv/logs/$host/$ano/$mes/$dia/
tar -xjf logs.bz
#####################################################################################################
