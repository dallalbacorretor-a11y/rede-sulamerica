# Gera o site da rede hospitalar Sul América (Adesão) a partir do CSV filtrado da ANS.
# Uso: python gerar_site.py   (lê rede_hospitalar_sulamerica.csv + cache_cnes.json, grava index.html)
import csv, json, os, re, datetime
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
PLANOS = ["Clássico 100", "Especial 100 RC", "Especial 100 R.1"]
dig = lambda s: re.sub(r"\D", "", s or "")

def titulo(s):
    s = re.sub(r"\s+", " ", (s or "").strip())
    peq = {"DE", "DA", "DO", "DAS", "DOS", "E"}
    sig = {"LTDA", "S/A", "SA", "ME", "EPP", "UTI", "SUS", "HC", "HU", "UPA", "CTI", "ABC", "AACD", "INCOR", "UNIMED"}
    out = []
    for i, w in enumerate(s.split(" ")):
        u = w.upper()
        out.append(u if u in sig or (len(u) <= 3 and not re.search(r"[AEIOUÁÉÍÓÚÂÊÔÃÕ]", u)) else
                   (w.lower() if i and u in peq else w.capitalize()))
    return " ".join(out)

rows = list(csv.DictReader(open(os.path.join(AQUI, "rede_hospitalar_sulamerica.csv"), encoding="utf-8-sig"), delimiter=";"))
ativos = [r for r in rows if not (r.get("DT_VINCULO_FIM") or "").strip()]
atual = max((r.get("DT_ATUALIZACAO") or "" for r in rows), default="")
print(len(rows), "linhas ·", len(ativos), "ativas · atualização ANS", atual)

MUN = json.load(open(os.path.join(AQUI, "municipios_ibge.json"), encoding="utf-8"))
CN = json.load(open(os.path.join(AQUI, "cache_cnes.json"), encoding="utf-8"))
def tel(t):
    d = dig(t)
    return f"({d[:2]}) {d[2:-4]}-{d[-4:]}" if len(d) >= 10 else (t or "")

H = {}
for r in ativos:
    cnpj = dig(r["CD_CNPJ_ESTB_SAUDE"]); cnes = dig(r["CD_CNES"]); cm = dig(r["CD_MUNICIPIO"])[:6]
    chave = (r["SG_UF"], cm, cnes or cnpj or r["NM_ESTABELECIMENTO_SAUDE"].upper())
    if chave not in H:
        c = CN.get(cnes) if isinstance(CN.get(cnes), dict) else {}
        fan = (c.get("nome_fantasia") or "").strip(); raz = (c.get("nome_razao_social") or "").strip()
        if fan and raz and (len(fan) <= 6 or " " not in fan.strip()):   # fantasia = sigla -> usa razão social
            nome, raz_t = f"{titulo(raz)} ({fan.upper()})", ""
        else:
            nome = titulo(fan or raz or r["NM_ESTABELECIMENTO_SAUDE"])
            raz_t = titulo(raz) if raz and raz.upper() != fan.upper() else ""
        end = titulo(" ".join(x for x in [c.get("endereco_estabelecimento") or "", (c.get("numero_estabelecimento") or "").strip()] if x))
        H[chave] = {"n": nome, "rz": raz_t, "cnpj": cnpj, "cnes": cnes, "uf": r["SG_UF"],
                    "mun": MUN.get(cm, titulo(r["NM_MUNICIPIO"]) or cm), "p": 0, "ps": 0,
                    "end": end, "bai": titulo(c.get("bairro_estabelecimento") or ""),
                    "cep": dig(c.get("codigo_cep_estabelecimento")), "tel": tel(c.get("numero_telefone_estabelecimento")),
                    "lat": round(c.get("latitude_estabelecimento_decimo_grau") or 0, 5),
                    "lng": round(c.get("longitude_estabelecimento_decimo_grau") or 0, 5),
                    "fl": (1 if c.get("estabelecimento_possui_centro_obstetrico") == 1 else 0)
                          | (2 if c.get("estabelecimento_possui_centro_neonatal") == 1 else 0)}
    h = H[chave]; b = 1 << PLANOS.index(r["PLANO_MAZZA"])
    h["p"] |= b
    if (r.get("LG_URGENCIA_EMERGENCIA") or "").strip() == "1": h["ps"] |= b

ufs = sorted({h["uf"] for h in H.values()})
lista = sorted(H.values(), key=lambda h: (h["uf"], h["mun"], -bin(h["p"]).count("1"), -bin(h["ps"]).count("1"), h["n"]))
a_, m_, d_ = atual.split("-") if "-" in atual else ("", "", atual)
dados = {
    "planos": PLANOS, "atual": f"{d_}/{m_}/{a_}" if a_ else atual,
    "gerado": datetime.date.today().strftime("%d/%m/%Y"),
    "h": [[h["uf"], h["mun"], h["n"], h["rz"], h["cnpj"], h["cnes"], h["p"], h["ps"], h["end"], h["bai"],
           h["cep"], h["tel"], h["lat"], h["lng"], h["fl"]] for h in lista],
}
print(len(lista), "hospitais únicos em", len(ufs), "UFs")
print("por plano:", {p: sum(1 for h in lista if h["p"] >> i & 1) for i, p in enumerate(PLANOS)})
print("sem município:", sum(1 for h in lista if not h["mun"] or h["mun"].isdigit()))

tpl = open(os.path.join(AQUI, "modelo-site.html"), encoding="utf-8").read()

html = tpl.replace("/*__DADOS__*/null", json.dumps(dados, ensure_ascii=False, separators=(",", ":")))
open(os.path.join(AQUI, "index.html"), "w", encoding="utf-8").write(html)
print("index.html", len(html) // 1024, "KB")
