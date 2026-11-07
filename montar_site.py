"""Monta index.html da REDE SUL AMÉRICA (Clássico 100 e Especial 100) NO PADRÃO DAS REDES MAZZA.

Página = a mesma da Bradesco/SulAmérica do repositório rede-amil-bradesco (bradesco/index.html,
baixada na hora para herdar as melhorias de lá), com os dados trocados.

Dados:
  1. busca_pme/<UF>/<CIDADE>.json — rede COMPLETA (hospitais, clínicas, laboratórios, imagem e
     médicos) da busca oficial da Sul América, consulta de 25/09/2026 (a mesma da Central de Rede).
     As cidades que estão aqui usam só esta fonte.
  2. rede_hospitalar_sulamerica.csv (filtrar_ans.py) + cache_cnes.json (enriquecer_cnes.py) — rede
     HOSPITALAR dos mesmos planos no resto do Brasil, pela base aberta da ANS.

Formato (o mesmo do montar_sulamerica.py):
  pr: [nome, cidade, bairro, [codigos], tipo, [especialidade, planos, ...],
       [[[servico por plano]], exames, 0], [endereco, telefones, "", cnpj, cep]]
  tipo: 0 clínica, 1 hospital, 2 laboratório, 3 médico, 4 centro de imagem.

Uso: python montar_site.py
"""
import csv, json, re, urllib.request
from datetime import date
from pathlib import Path

import sa_comum as SA      # funções do montar_sulamerica.py (classificação, nomes de especialidade)

RAIZ = Path(__file__).resolve().parent
MODELO_DIR = RAIZ / "modelo"
BUSCA = RAIZ / "busca_pme"
BASE = "https://raw.githubusercontent.com/dallalbacorretor-a11y/rede-amil-bradesco/main/"
REDES = "https://dallalbacorretor-a11y.github.io/rede-amil-bradesco/"
PORTAL = "https://portal.sulamericaseguros.com.br/rede-credenciada"
SITE = "https://dallalbacorretor-a11y.github.io/rede-sulamerica/"
PLANOS = [("classico100", "Clássico 100 Enfermaria", "Clássico 100"),
          ("especial100", "Especial 100", "Especial 100")]
ANS_PLANO = {"Clássico 100": 0, "Especial 100": 1}
dig = lambda s: re.sub(r"\D", "", str(s or ""))
sem_acento, titulo = SA.sem_acento, SA.titulo


def baixar_modelo():
    MODELO_DIR.mkdir(exist_ok=True)
    for f in ("bradesco/index.html", "bradesco/pdf-rede.js", "bradesco/pdfmake.min.js",
              "bradesco/fontes-pdf.js", "operadoras.js"):
        destino = MODELO_DIR / Path(f).name
        try:
            with urllib.request.urlopen(BASE + f, timeout=60) as r:
                destino.write_bytes(r.read())
        except Exception as e:
            if not destino.exists(): raise SystemExit(f"não baixei {f}: {e}")
            print(f"  (sem internet para {f}; usando a cópia local)")


def tel(t):
    d = dig(t)
    return f"({d[:2]}) {d[2:-4]}-{d[-4:]}" if len(d) >= 10 else (t or "")


def dados():
    ufs, cids, geo, bai, esp, nom, serv, pr, consulta = [], [], [], [], [], [], [""], [], {}
    idx = lambda lista, v: lista.index(v) if v in lista else (lista.append(v) or len(lista) - 1)
    pts = {}

    def cidade(uf, nome, data):
        iu = idx(ufs, uf)
        if [iu, nome] not in cids:
            cids.append([iu, nome]); geo.append(None); consulta[str(len(cids) - 1)] = data
        return cids.index([iu, nome])

    # ---- 1) rede completa da busca oficial (Curitiba e região)
    nomes_esp = {int(k): SA.legivel(v) for k, v in
                 json.loads((BUSCA / "especialidades.json").read_text(encoding="utf-8")).items()}
    cobertas, datas = set(), set()
    for arq in sorted(BUSCA.glob("*/*.json")):
        d = json.loads(arq.read_text(encoding="utf-8"))
        if not d["unidades"]: continue
        uf, nome_c = d["uf"], sem_acento(d["cidade"])
        data = "/".join(reversed(d["data"].split("-"))); datas.add(data)
        ic = cidade(uf, nome_c, data); cobertas.add((uf, nome_c))
        for u in d["unidades"]:
            if u.get("lat"): pts.setdefault(ic, []).append((u["lat"], u["lon"]))
            t = SA.tipo_de(u)
            sub = []
            for e in sorted({e for es in u["esp"].values() for e in es}):
                mask = sum(1 << b for b, (p, _, _) in enumerate(PLANOS) if e in u["esp"].get(p, []))
                sub += [idx(esp, nomes_esp.get(e, str(e))), mask]
            blocos = [[idx(serv, SA.servicos(u, p)) for p, _, _ in PLANOS]] if t == 1 else 0
            exames = sum(1 << b for b, (p, _, _) in enumerate(PLANOS)
                         if set(u["esp"].get(p, [])) & (SA.LAB | SA.IMAGEM))
            end = titulo(u["end"]) + (", " + u["num"] if u.get("num") else "") + \
                (" " + titulo(u["compl"]) if u.get("compl") else "")
            fones = " · ".join(dict.fromkeys(u.get("tel") or []))[:80]
            pr.append([idx(nom, re.sub(r"\s+", " ", u["nome"]).strip()), ic, idx(bai, titulo(u.get("bairro"))),
                       [], t, sub, [blocos, exames, 0],
                       [end, fones, "", u.get("cnpj") or "", dig(u.get("cep"))]])
    n_busca = len(pr)
    ref_busca = sorted(datas, key=lambda x: x.split("/")[::-1])[-1] if datas else ""

    # ---- 2) rede hospitalar da ANS no resto do Brasil
    rows = [r for r in csv.DictReader(open(RAIZ / "rede_hospitalar_sulamerica.csv", encoding="utf-8-sig"), delimiter=";")
            if not (r.get("DT_VINCULO_FIM") or "").strip()]
    MUN = json.loads((RAIZ / "municipios_ibge.json").read_text(encoding="utf-8"))
    CN = json.loads((RAIZ / "cache_cnes.json").read_text(encoding="utf-8"))
    atual = max(r["DT_ATUALIZACAO"] for r in rows)
    ref_ans = "/".join(reversed(atual.split("-")))
    U = {}
    for r in rows:
        cnes = dig(r["CD_CNES"]); cm = dig(r["CD_MUNICIPIO"])[:6]
        nome_c = sem_acento(MUN.get(cm, r["NM_MUNICIPIO"]) or cm)
        if (r["SG_UF"], nome_c) in cobertas: continue
        k = (r["SG_UF"], cm, cnes or dig(r["CD_CNPJ_ESTB_SAUDE"]) or r["NM_ESTABELECIMENTO_SAUDE"])
        u = U.setdefault(k, {"r": r, "cnes": cnes, "cid": nome_c, "p": 0, "ps": 0})
        b = 1 << ANS_PLANO[r["PLANO_MAZZA"]]
        u["p"] |= b
        if (r["LG_URGENCIA_EMERGENCIA"] or "").strip() == "1": u["ps"] |= b
    for u in sorted(U.values(), key=lambda u: (u["r"]["SG_UF"], u["cid"])):
        r = u["r"]; c = CN.get(u["cnes"]) if isinstance(CN.get(u["cnes"]), dict) else {}
        ic = cidade(r["SG_UF"], u["cid"], ref_ans)
        lat, lng = c.get("latitude_estabelecimento_decimo_grau"), c.get("longitude_estabelecimento_decimo_grau")
        if lat and lng: pts.setdefault(ic, []).append((lat, lng))
        fan = (c.get("nome_fantasia") or "").strip(); raz = (c.get("nome_razao_social") or "").strip()
        nome = f"{titulo(raz)} ({fan.upper()})" if fan and raz and (len(fan) <= 6 or " " not in fan) \
            else titulo(fan or raz or r["NM_ESTABELECIMENTO_SAUDE"])
        obst = c.get("estabelecimento_possui_centro_obstetrico") == 1
        sub = [idx(esp, "Internação"), u["p"]]
        if u["ps"]: sub += [idx(esp, "Pronto-socorro"), u["ps"]]
        if obst: sub += [idx(esp, "Maternidade"), u["p"]]
        servs = []
        for b in range(len(PLANOS)):
            if not (u["p"] >> b & 1): servs.append(0); continue
            servs.append(idx(serv, "/".join(["H"] + (["P.S"] if u["ps"] >> b & 1 else []) + (["M"] if obst else []))))
        end = titulo(c.get("endereco_estabelecimento") or "")
        if (c.get("numero_estabelecimento") or "").strip(): end += ", " + c["numero_estabelecimento"].strip()
        pr.append([idx(nom, nome), ic, idx(bai, titulo(c.get("bairro_estabelecimento") or "")),
                   [int(u["cnes"])] if u["cnes"] else [], 1, sub, [[servs], 0, 0],
                   [end, tel(c.get("numero_telefone_estabelecimento")), "", dig(r["CD_CNPJ_ESTB_SAUDE"]),
                    dig(c.get("codigo_cep_estabelecimento"))]])

    for i in range(len(cids)):
        p = pts.get(i) or [(-15.8, -47.9)]
        geo[i] = [round(sum(x[0] for x in p) / len(p), 4), round(sum(x[1] for x in p) / len(p), 4)]
    print(f"{n_busca} prestadores da busca oficial ({len(cobertas)} cidades) + {len(pr) - n_busca} hospitais da ANS")
    return {"ref": ref_busca or ref_ans, "refAns": ref_ans,
            "fonte": "busca de rede referenciada da Sul América Saúde + base aberta da ANS",
            "gerado": date.today().strftime("%d/%m/%Y"),
            "corretor": {"corretora": "Mazza Broker", "nome": "Alan Vinicius Dall Alba",
                         "fone": "(41) 99547-6715", "email": "alan.vinicius@mazzabroker.com.br"},
            "logo": "", "logoBranca": "", "planos": [p[1] for p in PLANOS],
            "grupos": [{"rot": p[2], "bits": [b], "sub": None} for b, p in enumerate(PLANOS)],
            "hospRef": {}, "labRef": {}, "espFora": [], "uf": ufs, "cid": cids, "geo": geo, "bai": bai,
            "esp": esp, "nom": nom, "serv": serv, "pr": pr, "consulta": consulta}


def troca(html, velho, novo, regex=False, minimo=1):
    n = len(re.findall(velho, html, flags=re.S)) if regex else html.count(velho)
    if n < minimo:
        raise SystemExit(f"o modelo mudou: não achei {velho[:70]!r}")
    return re.sub(velho, lambda m: novo, html, flags=re.S) if regex else html.replace(velho, novo)


COMO_LER = f"""<div class="corpo">
    <div>
      <h3>Uma linha por prestador</h3>
      <p>O ✔ à direita diz em quais planos ele está. Sob o nome vêm o bairro, a cidade, as
        especialidades, o endereço e o telefone. As etiquetas dizem o que mais ele faz:
        <b>internação</b>, <b>pronto-socorro</b>, <b>maternidade</b>, <b>hospital-dia</b> e
        <b>exames</b>.</p>
    </div>
    <div>
      <h3>Clássico 100 e Especial 100</h3>
      <p>Os dois planos da Sul América Saúde (PME; Empresarial e PME Mais têm a mesma rede).
        Clique em um ou nos dois: <b>atende a qualquer um</b> mostra quem está em pelo menos um;
        <b>atende a todos</b>, só a rede dos dois. A aba <b>Entre planos</b> mostra o que muda
        de um para o outro.</p>
    </div>
    <div>
      <h3>Rede completa e rede hospitalar</h3>
      <p><b>Curitiba e região metropolitana</b>: rede completa — hospitais, clínicas, médicos,
        laboratórios e imagem — da busca oficial da Sul América. <b>Demais cidades do Brasil</b>:
        rede hospitalar dos mesmos planos, pela base oficial da ANS.</p>
    </div>
    <div>
      <h3>De onde vem</h3>
      <p>Da busca de rede referenciada do site da Sul América Saúde (plano a plano e especialidade a
        especialidade) e da base aberta da <b>ANS</b> “Produtos e Prestadores Hospitalares”, com
        endereço e telefone do <b>CNES</b> (Ministério da Saúde).</p>
    </div>
    <div>
      <h3>Antes de fechar</h3>
      <p>A rede é definida e alterada só pela operadora. <b>Confirme no
        <a href="{PORTAL}" target="_blank" rel="noopener">portal da Sul América Saúde</a> antes
        de contratar.</b></p>
    </div>
  </div>
</details>"""

RODAPE = f"""<footer>
  <span class="selo-rodape" id="seloRod">Mazza Broker</span>
  <b>Versão sempre atualizada:</b>
  <a href="{SITE}" style="color:var(--ouro)">{SITE.replace("https://", "").rstrip("/")}</a><br>
  <span id="fonteDetalhe"></span><br>
  Gerado em <span id="ger"></span> · <span id="rodCorr"></span><br>
  Curitiba e região: busca oficial da Sul América. Demais cidades: rede hospitalar pela base aberta da ANS,
  com endereço e telefone do CNES. A classificação em hospital, laboratório, imagem e clínica segue a
  categoria e as especialidades informadas pela Sul América.
  <b>A rede é definida e alterada exclusivamente pela operadora. Confirme no
  <a href="{PORTAL}" target="_blank" rel="noopener" style="color:var(--ouro)">portal da Sul América
  Saúde</a> antes de contratar.</b>
</footer>"""


def pagina(D):
    html = (MODELO_DIR / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")
    i = html.index("const DADOS = "); j = html.index("\n", i)
    html = html[:i] + "@@DADOS@@" + html[j:]
    html = troca(html, r"<title>.*?</title>", "<title>Rede Sul América Saúde</title>", regex=True)
    html = troca(html, r'<img class="logo-op" id="logoOp"[^>]*>\n?', "", regex=True)
    html = troca(html, "--topo:#8b0633;", "--topo:#0b2d5c;")
    html = troca(html, "--topo-fraco:#e9c2ce;", "--topo-fraco:#c8d6ec;")
    html = troca(html, "--topo:#6b0427;", "--topo:#0a2347;")
    html = troca(html, "--topo-fraco:#e0aebe;", "--topo-fraco:#b9c9e2;")
    html = troca(html, "--p0:#a3123c; --p1:#b0552a;", "--p0:#c2560c; --p1:#1d5089;")
    html = troca(html, "--p0-bg:#fbecf0; --p1-bg:#fbefe8;", "--p0-bg:#fbefe6; --p1-bg:#eaf0f9;")
    html = troca(html, "--p0:#f08aa6; --p1:#e5a071;", "--p0:#e8a06b; --p1:#8fb6e8;")
    html = troca(html, "--p0-bg:#2a1520; --p1-bg:#2a1c14;", "--p0-bg:#2a1c14; --p1-bg:#14202f;")
    html = troca(html, r'<div class="corpo">.*?</details>', COMO_LER, regex=True)
    html = troca(html, r"<footer>.*?</footer>", RODAPE, regex=True)
    html = troca(html, r"const PORTAL = '[^']*';", f"const PORTAL = '{PORTAL}';", regex=True)
    html = troca(html, "    '<b>Consultas</b> · Brasil · buscador ' + esc(DADOS.ref),\n"
                       "    linha('Internação', HREF),\n    linha('Exames', LREF)\n", "")
    html = troca(html, r"det\.push\('<b>Fontes:</b> ' \+ esc\(DADOS\.fonte\).*?\);\n",
                 "det.push('<b>Fontes:</b> busca oficial da Sul América de ' + esc(DADOS.ref) + "
                 "' (Curitiba e região, rede completa) e base aberta da ANS de ' + esc(DADOS.refAns) + "
                 "' (rede hospitalar nas demais cidades). <b>Planos:</b> ' + esc(PRODUTOS.join(' e ')) + ' (PME).');\n",
                 regex=True)
    html = troca(html, r"det\.push\('Cobertura: as listas.*?\);\n",
                 "det.push('Cobertura: ' + CID.length.toLocaleString('pt-BR') + ' cidades em ' + "
                 "UF.length + ' estados.');\n", regex=True)
    html = troca(html, "consultas, exames, internação e pronto-socorro, com endereço e telefone), conferida contra as ' +\n"
                       "      'listas abaixo: quem está nelas e não aparece na busca, nem pelo nome, continua marcado.');",
                 "consultas, exames, internação e pronto-socorro, com endereço e telefone).');")
    html = troca(html, "https://www.bradescoseguros.com.br/clientes/produtos/plano-saude/consulta-de-rede-referenciada/",
                 PORTAL, minimo=0)
    html = troca(html, '<script src="../operadoras.js" data-operadora="bradesco"></script>',
                 '<script src="operadoras.js" data-operadora="sulamerica"></script>')
    html = html.replace("Bradesco Saúde", "Sul América Saúde").replace("Bradesco", "Sul América")
    html = html.replace("SulAmérica", "Sul América")
    html = html.replace("@@DADOS@@", "const DADOS = " + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";")
    return html


def barra():
    """operadoras.js do rede-amil-bradesco com links absolutos; a aba SulAmérica aponta para este site."""
    js = (MODELO_DIR / "operadoras.js").read_text(encoding="utf-8")
    js = troca(js, '{ id: "sulamerica", nome: "SulAmérica", longo: " Saúde" },',
               '{ id: "sulamerica", nome: "SulAmérica", longo: " Saúde", url: "' + SITE + '" },')
    js = troca(js, 'inicio.href = "../";', f'inicio.href = "{REDES}";')
    js = troca(js, 'a.href = "../" + op.id + "/";', f'a.href = op.url || ("{REDES}" + op.id + "/");')
    return js


def main():
    baixar_modelo()
    D = dados()
    (RAIZ / "index.html").write_text(pagina(D), encoding="utf-8")
    (RAIZ / "operadoras.js").write_text(barra(), encoding="utf-8")
    for f in ("pdf-rede.js", "pdfmake.min.js", "fontes-pdf.js"):
        (RAIZ / f).write_bytes((MODELO_DIR / f).read_bytes())
    tipos = [sum(1 for p in D["pr"] if p[4] == t) for t in range(5)]
    print(f"index.html: {len(D['pr'])} prestadores em {len(D['cid'])} cidades / {len(D['uf'])} UFs "
          f"(clínicas {tipos[0]}, hospitais {tipos[1]}, labs {tipos[2]}, médicos {tipos[3]}, imagem {tipos[4]}), "
          f"{(RAIZ / 'index.html').stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
