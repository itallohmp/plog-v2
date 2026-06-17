# PLog

PLog é uma ferramenta backend em Python + FastAPI para consultar flows de rede (nfcapd) de forma estruturada. O usuário seleciona uma data no frontend, a API conecta via SSH ao servidor de flows, localiza os arquivos nfcapd correspondentes e usa o `nfdump` para exportar os dados em JSON, que são validados com Pydantic e exibidos na interface.

## Visão geral

Coletar flows de acesso à internet a partir dos arquivos nfcapd, extrair campos relevantes (IP, timestamp, NAT, porta, destino, roteador), aplicar filtros e expor os resultados via API.

A aplicação permite:

- conectar remotamente via SSH ao servidor de flows;
- localizar automaticamente os arquivos nfcapd da data selecionada;
- exportar os flows em JSON via `nfdump` (sem regex);
- validar e estruturar os dados com Pydantic;
- filtrar por IP, porta e intervalo de horas;
- paginar resultados;
- servir o frontend pela pasta `static`.

## Configuração (variáveis de ambiente)

Nenhuma credencial fica no código. Configure no servidor:

- `PLOG_FLOW_SSH_HOST` , `PLOG_FLOW_SSH_PORT`, `PLOG_FLOW_SSH_USER`
- `PLOG_FLOW_SSH_KEY_PATH` (recomendado) ou `PLOG_FLOW_SSH_PASSWORD`
- `PLOG_FLOW_SSH_KNOWN_HOSTS` (recomendado para validar o host)
- `PLOG_FLOW_REMOTE_DIR` 
- `PLOG_FLOW_DAY_DIR_FORMAT` (padrão `%Y-%m-%d`)
- `PLOG_NFDUMP_BIN` (padrão `nfdump`), `PLOG_NFDUMP_TIMEOUT`
- `PLOG_FLOW_LOCAL_PATH` (opcional): caminho de um arquivo JSON ou pasta com `.json` para testes locais sem SSH/VPN. Quando definido, o backend lê desse caminho em vez de conectar no servidor.

## Tecnologias utilizadas

- Python
- FastAPI
- Paramiko
- HTML
- CSS
- JavaScript

## Funcionalidades

- Verificação de saúde da API (`/health`)
- Consulta de flows por data (`/flows`)
- Conexão SSH ao servidor de flows (Paramiko)
- Exportação via `nfdump -R <pasta_da_hora> -o json`
- Validação e estruturação com Pydantic
- Filtro por:
  - Data
  - IP
  - Porta (inclui faixa de bloco NAT quando disponível)
  - Intervalo de horas
- Paginação de resultados
- Serviço de arquivos estáticos
- Tratamento de erros (404 sem dados, 502 falha SSH/nfdump, 422 parâmetros)


## Como a aplicação funciona
O funcionamento da aplicação é dividido em duas partes principais: a consulta remota de logs via SSH e o processamento de logs armazenados localmente. Quando a aplicação é iniciada, ela cria uma API com FastAPI, configura o CORS para permitir chamadas do frontend em ambiente de desenvolvimento e monta a pasta static, responsável por servir os arquivos visuais da interface, como HTML, CSS e JavaScript.
A aplicação possui um endpoint simples de verificação chamado /health, que retorna o status da API, e também um endpoint raiz /, que entrega diretamente o arquivo index.html, permitindo que a interface seja aberta no navegador.
Na parte de leitura remota, a aplicação utiliza a biblioteca Paramiko para estabelecer uma conexão SSH segura com um servidor remoto. Para isso, ela carrega uma chave privada localizada em /home/plog/.ssh/id_rsa, autentica no servidor com o usuário configurado e executa o comando tail -n {limit} /var/log/syslog, retornando as últimas linhas do arquivo de log do sistema. Essas linhas são então lidas, decodificadas e analisadas. Caso o comando remoto falhe ou a conexão apresente algum problema, a aplicação devolve uma resposta de erro apropriada.
Depois que os logs são obtidos, cada linha passa por um processo de parse, feito com expressão regular. Esse parser foi criado para identificar registros que contenham informações como data, protocolo, origem, NAT, destino e destino final. Quando uma linha corresponde ao padrão esperado, a aplicação extrai essas informações e as organiza em formato estruturado, facilitando o consumo pelo frontend ou por outras integrações.
Além da leitura remota, o sistema também trabalha com logs armazenados localmente em uma estrutura de diretórios organizada por IP da rota, ano, mês e dia. Quando o endpoint /logs/filter é chamado, a aplicação verifica se já existem arquivos de log disponíveis naquele diretório. Se não houver arquivos locais, ela executa um script externo de download. Caso existam apenas arquivos compactados com extensão .bz, outro script é executado para realizar a descompactação e gerar os arquivos .log.
Com os arquivos disponíveis, a aplicação ordena os logs e aplica filtros com base nos parâmetros recebidos na requisição. É possível filtrar por IP NAT, porta NAT, dia, mês, ano, intervalo de horário e palavra-chave. Também existe suporte à paginação, para evitar carregar uma quantidade excessiva de registros de uma só vez. Durante esse processo, cada linha dos arquivos é lida, validada, filtrada e convertida em JSON.
O retorno do endpoint /logs/filter é feito com StreamingResponse, utilizando o formato NDJSON. Isso significa que os resultados são enviados de forma incremental, linha por linha, o que é útil para grandes volumes de dados e melhora a experiência do usuário na interface.
De forma geral, o PLog funciona como uma ponte entre a infraestrutura de logs e uma interface web mais amigável. Em vez de depender exclusivamente do terminal SSH e de buscas manuais em arquivos, o sistema automatiza a obtenção, processamento, filtragem e apresentação dos logs, tornando a consulta mais rápida, padronizada e eficiente.

## Estrutura do projeto

```bash
.
├── main.py
├── static/
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   └── ...
└── README.md
