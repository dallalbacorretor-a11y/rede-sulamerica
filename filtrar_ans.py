# Filtra a base aberta da ANS (produtos_e_prestadores_hospitalares.zip) e
# grava a rede hospitalar ATIVA dos planos Sul América Clássico 100 e Especial 100 (PME/Empresarial).
# Uso: python filtrar_ans.py "<base.zip>"   -> gera rede_hospitalar_sulamerica.csv ao lado
import csv, io, os, sys, zipfile, re

PLANOS = {  # registro ANS (só dígitos) -> plano (rede PME/Empresarial, a mesma da busca da Sul América)
    "500529249": "Clássico 100", "500521243": "Clássico 100", "500530242": "Clássico 100", "500522241": "Clássico 100",
    "488497213": "Especial 100", "469523132": "Especial 100", "499569244": "Especial 100", "473982155": "Especial 100",
    "499559247": "Especial 100", "499570248": "Especial 100", "499558249": "Especial 100", "463421107": "Especial 100",
}
OPERADORAS = {"6246", "416428"}   # Sul América Cia de Seguro Saúde e Sul América Serviços de Saúde
SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rede_hospitalar_sulamerica.csv")
dig = lambda s: re.sub(r"\D", "", s or "")

z = zipfile.ZipFile(sys.argv[1])
nomes = sorted(n for n in z.namelist() if n.lower().endswith(".csv"))
print(len(nomes), "arquivos (um por UF)")
out, n, achou_op = [], 0, 0
for nome in nomes:
    head = z.open(nome).read(4096)
    try: head.decode("utf-8"); enc = "utf-8-sig"
    except UnicodeDecodeError as e: enc = "utf-8-sig" if e.start > 4000 else "latin-1"
    sep = ";" if head.count(b";") > head.count(b",") else ","
    f = io.TextIOWrapper(z.open(nome), encoding=enc, errors="replace", newline="")
    rd = csv.DictReader(f, delimiter=sep)
    rd.fieldnames = [c.strip().lstrip("﻿").strip('"') for c in rd.fieldnames]
    antes = len(out)
    for r in rd:
        n += 1
        if dig(r["CD_OPERADORA"]).lstrip("0") not in OPERADORAS: continue
        achou_op += 1
        reg = dig(r["CD_PLANO"])
        if reg not in PLANOS: continue
        out.append({**r, "PLANO_MAZZA": PLANOS[reg]})
    print(f"  {nome}: +{len(out)-antes}", flush=True)
print(f"{n:,} linhas lidas · {achou_op:,} da Sul América · {len(out):,} dos planos")

with open(SAIDA, "w", encoding="utf-8-sig", newline="") as g:
    w = csv.DictWriter(g, fieldnames=list(out[0].keys()), delimiter=";")
    w.writeheader(); w.writerows(out)
print("gravado:", SAIDA)
