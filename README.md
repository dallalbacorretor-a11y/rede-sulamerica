# Rede Sul América Saúde — Mazza Broker

Rede referenciada da Sul América Saúde dos planos **Clássico 100 Enfermaria** e **Especial 100**
(PME; Empresarial e PME Mais têm a mesma rede), no padrão das redes Mazza (mesma página da
Bradesco/SulAmérica do `rede-amil-bradesco`).

- **Curitiba e região metropolitana (11 cidades):** rede **completa** — hospitais, clínicas, médicos,
  laboratórios e imagem — da busca oficial da Sul América (consulta de 25/09/2026, a mesma da Central de Rede).
- **Demais cidades do Brasil:** rede **hospitalar** dos mesmos planos, pela base aberta da ANS
  "Produtos e Prestadores Hospitalares", com endereço e telefone do CNES.

Registros ANS usados (portal Sul América, detalhes do plano):
Clássico 100 (557/69300): 500.529/24-9, 500.521/24-3, 500.530/24-2, 500.522/24-1 ·
Especial 100 (553/17924): 488.497/21-3, 469.523/13-2, 499.569/24-4, 473.982/15-5, 499.559/24-7,
499.570/24-8, 499.558/24-9, 463.421/10-7.

## Arquivos

| Arquivo | O que é |
|---|---|
| `busca_pme/` | rede completa por cidade (JSON) + nomes das especialidades |
| `sa_comum.py` | classificação dos prestadores (cópia do `montar_sulamerica.py` do rede-amil-bradesco) |
| `filtrar_ans.py` | filtra a base da ANS pelos registros acima → `rede_hospitalar_sulamerica.csv` |
| `enriquecer_cnes.py` | endereço/telefone/maternidade pelo CNES (cache em `cache_cnes.json`) |
| `montar_site.py` | monta `index.html` no padrão (baixa o modelo em `modelo/`) |

## Como atualizar

```sh
# hospitais (a ANS atualiza todo mês): baixar produtos_e_prestadores_hospitalares.zip (≈1,4 GB)
# de https://dadosabertos.ans.gov.br/FTP/PDA/produtos_e_prestadores_hospitalares/
python filtrar_ans.py "caminho/produtos_e_prestadores_hospitalares.zip"
python enriquecer_cnes.py
python montar_site.py
git add -A && git commit -m "Atualiza rede" && git push
```

A busca do site da Sul América exige reCAPTCHA; os dados de `busca_pme/` vêm da consulta já feita e
guardada no `rede-amil-bradesco`. **Confirme sempre no portal da Sul América antes de contratar.**
