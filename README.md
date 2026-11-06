# Rede Hospitalar Sul América · Adesão — Mazza Broker

Consulta da **rede hospitalar** dos planos Sul América **Coletivo por Adesão** no Brasil inteiro,
por estado, cidade e plano, com pronto-socorro e maternidade:

| Plano | Registro ANS |
|---|---|
| Clássico 100 Enfermaria | 500.480/24-2 |
| Especial 100 RC | 495.735/23-1 |
| Especial 100 R.1 | 495.737/23-7 |

Abre filtrada por link: `?uf=PR&cidade=Curitiba` (e `&q=pilar` para buscar um nome).

## De onde vêm os dados

1. **ANS — dados abertos "Produtos e Prestadores Hospitalares"**
   (`dadosabertos.ans.gov.br/FTP/PDA/produtos_e_prestadores_hospitalares/`): a rede hospitalar que a
   operadora informa à ANS, por registro do produto. Entram só vínculos ativos (sem data de fim).
   Traz se o contrato inclui urgência/emergência (**PS**).
2. **CNES / Ministério da Saúde** (`apidadosabertos.saude.gov.br/cnes/estabelecimentos/<cnes>`):
   nome completo, endereço, bairro, telefone, coordenadas e se tem centro obstétrico (**Maternidade**).
3. **IBGE** (`servicodados.ibge.gov.br`): nome do município pelo código.

A base da ANS **não traz consultórios, clínicas e laboratórios** — só a rede hospitalar.
A busca do site da Sul América (rederef-saude) exige reCAPTCHA em cada pesquisa, por isso não é
usada aqui. **Confirme sempre no portal da Sul América antes de contratar.**

## Como atualizar (a ANS atualiza a base todo mês)

```sh
# 1) baixar produtos_e_prestadores_hospitalares.zip (≈1,4 GB) do link da ANS acima
python filtrar_ans.py "caminho/produtos_e_prestadores_hospitalares.zip"   # -> rede_hospitalar_sulamerica.csv
python enriquecer_cnes.py      # completa endereço/telefone dos hospitais novos (usa cache_cnes.json)
python gerar_site.py           # -> index.html
git add -A && git commit -m "Atualiza rede (ANS <data>)" && git push
```

Visual da página: `modelo-site.html` (o `gerar_site.py` injeta os dados nele).
