"""Monta index.html da rede Sul América Adesão NO PADRÃO DAS REDES MAZZA.

A página é a mesma da Bradesco/SulAmérica PME do repositório rede-amil-bradesco
(bradesco/index.html, baixada na hora para herdar as melhorias de lá), com os dados
trocados pelos da ANS + CNES. Mesmo formato de dados do montar_sulamerica.py de lá:
  pr: [nome, cidade, bairro, [codigos], tipo, [especialidade, planos, ...],
       [[[servico por plano]], exames, 0], [endereco, telefones, "", cnpj, cep]]

Uso: python montar_site.py   (lê rede_hospitalar_sulamerica.csv, cache_cnes.json, municipios_ibge.json)
"""
import csv, json, re, unicodedata, urllib.request
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
MODELO_DIR = RAIZ / "modelo"
BASE = "https://raw.githubusercontent.com/dallalbacorretor-a11y/rede-amil-bradesco/main/"
REDES = "https://dallalbacorretor-a11y.github.io/rede-amil-bradesco/"
PORTAL = "https://portal.sulamericaseguros.com.br/rede-credenciada"
SITE = "https://dallalbacorretor-a11y.github.io/rede-sulamerica/"
PLANOS = [("Clássico 100", "Clássico 100 Enfermaria", "500480242"),
          ("Especial 100 RC", "Especial 100 RC", "495735231"),
          ("Especial 100 R.1", "Especial 100 R.1", "495737237")]
dig = lambda s: re.sub(r"\D", "", str(s or ""))


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").upper()


def titulo(s):
    s = re.sub(r"\s+", " ", (s or "").strip())
    sig = {"LTDA", "S/A", "SA", "ME", "EPP", "UTI", "SUS", "HC", "HU", "UPA", "INCOR", "AACD", "FMUSP", "IPO", "INC"}
    out = []
    for i, w in enumerate(s.split(" ")):
        u = w.upper()
        if u in sig: out.append(u)
        elif i and u in ("DE", "DA", "DO", "DAS", "DOS", "E"): out.append(w.lower())
        else: out.append(w.capitalize())
    return " ".join(out)


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
    rows = [r for r in csv.DictReader(open(RAIZ / "rede_hospitalar_sulamerica.csv", encoding="utf-8-sig"), delimiter=";")
            if not (r.get("DT_VINCULO_FIM") or "").strip()]
    MUN = json.loads((RAIZ / "municipios_ibge.json").read_text(encoding="utf-8"))
    CN = json.loads((RAIZ / "cache_cnes.json").read_text(encoding="utf-8"))
    atual = max(r["DT_ATUALIZACAO"] for r in rows)
    ref = "/".join(reversed(atual.split("-")))
    bit = {p[2]: b for b, p in enumerate(PLANOS)}

    U = {}
    for r in rows:
        cnes = dig(r["CD_CNES"]); cm = dig(r["CD_MUNICIPIO"])[:6]
        k = (r["SG_UF"], cm, cnes or dig(r["CD_CNPJ_ESTB_SAUDE"]) or r["NM_ESTABELECIMENTO_SAUDE"])
        u = U.setdefault(k, {"r": r, "cnes": cnes, "cm": cm, "p": 0, "ps": 0})
        b = 1 << bit[dig(r["CD_PLANO"])]
        u["p"] |= b
        if (r["LG_URGENCIA_EMERGENCIA"] or "").strip() == "1": u["ps"] |= b

    ufs, cids, geo, bai, esp, nom, serv, pr, consulta = [], [], [], [], [], [], [""], [], {}
    idx = lambda lista, v: lista.index(v) if v in lista else (lista.append(v) or len(lista) - 1)
    pts = {}
    ordem = sorted(U.values(), key=lambda u: (u["r"]["SG_UF"], sem_acento(MUN.get(u["cm"], ""))))
    for u in ordem:
        r = u["r"]; c = CN.get(u["cnes"]) if isinstance(CN.get(u["cnes"]), dict) else {}
        uf = r["SG_UF"]; cidade = sem_acento(MUN.get(u["cm"], r["NM_MUNICIPIO"]) or u["cm"])
        iu = idx(ufs, uf)
        if [iu, cidade] not in cids:
            cids.append([iu, cidade]); geo.append(None); consulta[str(len(cids) - 1)] = ref
        ic = cids.index([iu, cidade])
        lat, lng = c.get("latitude_estabelecimento_decimo_grau"), c.get("longitude_estabelecimento_decimo_grau")
        if lat and lng: pts.setdefault(ic, []).append((lat, lng))

        fan = (c.get("nome_fantasia") or "").strip(); raz = (c.get("nome_razao_social") or "").strip()
        if fan and raz and (len(fan) <= 6 or " " not in fan):
            nome = f"{titulo(raz)} ({fan.upper()})"
        else:
            nome = titulo(fan or raz or r["NM_ESTABELECIMENTO_SAUDE"])
        obst = c.get("estabelecimento_possui_centro_obstetrico") == 1
        sub = [idx(esp, "Internação"), u["p"]]
        if u["ps"]: sub += [idx(esp, "Pronto-socorro"), u["ps"]]
        if obst: sub += [idx(esp, "Maternidade"), u["p"]]
        if c.get("estabelecimento_possui_centro_neonatal") == 1: sub += [idx(esp, "UTI neonatal"), u["p"]]
        servs = []
        for b in range(len(PLANOS)):
            if not (u["p"] >> b & 1): servs.append(0); continue
            s = ["H"] + (["P.S"] if u["ps"] >> b & 1 else []) + (["M"] if obst else [])
            servs.append(idx(serv, "/".join(s)))
        end = titulo(c.get("endereco_estabelecimento") or "")
        if (c.get("numero_estabelecimento") or "").strip(): end += ", " + c["numero_estabelecimento"].strip()
        pr.append([idx(nom, nome), ic, idx(bai, titulo(c.get("bairro_estabelecimento") or "")),
                   [int(u["cnes"])] if u["cnes"] else [], 1, sub, [[servs], 0, 0],
                   [end, tel(c.get("numero_telefone_estabelecimento")), "", dig(r["CD_CNPJ_ESTB_SAUDE"]),
                    dig(c.get("codigo_cep_estabelecimento"))]])
    for i in range(len(cids)):
        p = pts.get(i) or [(-15.8, -47.9)]
        geo[i] = [round(sum(x[0] for x in p) / len(p), 4), round(sum(x[1] for x in p) / len(p), 4)]
    return {"ref": ref, "fonte": "base aberta da ANS (Produtos e Prestadores Hospitalares) + CNES",
            "gerado": date.today().strftime("%d/%m/%Y"),
            "corretor": {"corretora": "Mazza Broker", "nome": "Alan Vinicius Dall Alba",
                         "fone": "(41) 99547-6715", "email": "alan.vinicius@mazzabroker.com.br"},
            "logo": "", "logoBranca": "", "planos": [p[1] for p in PLANOS],
            "grupos": [{"rot": p[0], "bits": [b], "sub": None} for b, p in enumerate(PLANOS)],
            "hospRef": {}, "labRef": {}, "espFora": [], "uf": ufs, "cid": cids, "geo": geo, "bai": bai,
            "esp": esp, "nom": nom, "serv": serv, "pr": pr, "consulta": consulta}


def troca(html, velho, novo, regex=False, minimo=1):
    n = len(re.findall(velho, html, flags=re.S)) if regex else html.count(velho)
    if n < minimo:
        raise SystemExit(f"o modelo mudou: não achei {velho[:70]!r}")
    return re.sub(velho, lambda m: novo, html, flags=re.S) if regex else html.replace(velho, novo)


COMO_LER = f"""<div class="corpo">
    <div>
      <h3>Uma linha por hospital</h3>
      <p>O ✔ à direita diz em quais planos ele está. Sob o nome vêm o bairro, a cidade, o
        endereço e o telefone. As etiquetas dizem o que ele faz no plano: <b>internação</b>,
        <b>pronto-socorro</b> e <b>maternidade</b>.</p>
    </div>
    <div>
      <h3>Clássico 100, Especial 100 RC e R.1</h3>
      <p>Os três planos Sul América <b>Coletivo por Adesão</b> (abrangência nacional). Clique em um
        ou mais: <b>atende a qualquer um</b> mostra quem está em pelo menos um; <b>atende a todos</b>,
        só quem está em todos os marcados. A aba <b>Entre planos</b> mostra o que muda de um para o outro.</p>
    </div>
    <div>
      <h3>Só a rede hospitalar</h3>
      <p>A base oficial da ANS traz os <b>hospitais</b> de cada plano. Consultórios, clínicas e
        laboratórios não estão nela: para esses, consulte a busca do site da Sul América.</p>
    </div>
    <div>
      <h3>De onde vem</h3>
      <p>Da base aberta da <b>ANS</b> “Produtos e Prestadores Hospitalares” (a rede que a Sul América
        informa à ANS, por registro do plano), com nome, endereço, telefone e maternidade do
        <b>CNES</b> (Ministério da Saúde).</p>
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
  Rede hospitalar dos planos Clássico 100 Enfermaria (ANS 500.480/24-2), Especial 100 RC (495.735/23-1)
  e Especial 100 R.1 (495.737/23-7), conforme a base aberta da ANS; endereço e telefone do CNES.
  <b>A rede é definida e alterada exclusivamente pela operadora. Confirme no
  <a href="{PORTAL}" target="_blank" rel="noopener" style="color:var(--ouro)">portal da Sul América
  Saúde</a> antes de contratar.</b>
</footer>"""


def pagina(D):
    html = (MODELO_DIR / "index.html").read_text(encoding="utf-8").replace("\r\n", "\n")
    i = html.index("const DADOS = "); j = html.index("\n", i)
    html = html[:i] + "@@DADOS@@" + html[j:]
    html = troca(html, r"<title>.*?</title>", "<title>Rede Sul América Adesão</title>", regex=True)
    html = troca(html, r'<img class="logo-op" id="logoOp"[^>]*>\n?', "", regex=True)
    html = troca(html, "--topo:#8b0633;", "--topo:#0b2d5c;")
    html = troca(html, "--topo-fraco:#e9c2ce;", "--topo-fraco:#c8d6ec;")
    html = troca(html, "--topo:#6b0427;", "--topo:#0a2347;")
    html = troca(html, "--topo-fraco:#e0aebe;", "--topo-fraco:#b9c9e2;")
    # Clássico laranja · Especial RC verde · Especial R.1 azul
    html = troca(html, "--p0:#a3123c; --p1:#b0552a;", "--p0:#c2560c; --p1:#1f7a52;")
    html = troca(html, "--p0-bg:#fbecf0; --p1-bg:#fbefe8;", "--p0-bg:#fbefe6; --p1-bg:#e6f3ec;")
    html = troca(html, "--p0:#f08aa6; --p1:#e5a071;", "--p0:#e8a06b; --p1:#7fd0a6;")
    html = troca(html, "--p0-bg:#2a1520; --p1-bg:#2a1c14;", "--p0-bg:#2a1c14; --p1-bg:#12261c;")
    html = troca(html, r'<div class="corpo">.*?</details>', COMO_LER, regex=True)
    html = troca(html, r"<footer>.*?</footer>", RODAPE, regex=True)
    html = troca(html, r"const PORTAL = '[^']*';", f"const PORTAL = '{PORTAL}';", regex=True)
    html = troca(html, "    '<b>Consultas</b> · Brasil · buscador ' + esc(DADOS.ref),\n"
                       "    linha('Internação', HREF),\n    linha('Exames', LREF)\n", "")
    html = troca(html, r"det\.push\('<b>Fontes:</b> ' \+ esc\(DADOS\.fonte\).*?\);\n",
                 "det.push('<b>Fonte:</b> base aberta da ANS de ' + esc(DADOS.ref) + ' + CNES. <b>Planos:</b> ' + "
                 "esc(PRODUTOS.join(', ')) + ' (Coletivo por Adesão).');\n", regex=True)
    html = troca(html, r"det\.push\('Cobertura: as listas.*?\);\n",
                 "det.push('Cobertura: ' + CID.length.toLocaleString('pt-BR') + ' cidades em ' + "
                 "UF.length + ' estados (só rede hospitalar).');\n", regex=True)
    html = troca(html, "consultas, exames, internação e pronto-socorro, com endereço e telefone), conferida contra as ' +\n"
                       "      'listas abaixo: quem está nelas e não aparece na busca, nem pelo nome, continua marcado.');",
                 "internação, pronto-socorro e maternidade, com endereço e telefone).');")
    html = troca(html, "https://www.bradescoseguros.com.br/clientes/produtos/plano-saude/consulta-de-rede-referenciada/",
                 PORTAL, minimo=0)
    html = troca(html, '<script src="../operadoras.js" data-operadora="bradesco"></script>',
                 '<script src="operadoras.js" data-operadora="sulamerica-adesao"></script>')
    html = html.replace("Bradesco Saúde", "Sul América Saúde").replace("Bradesco", "Sul América")
    html = html.replace("SulAmérica", "Sul América")
    html = html.replace("@@DADOS@@", "const DADOS = " + json.dumps(D, ensure_ascii=False, separators=(",", ":")) + ";")
    return html


def barra():
    """operadoras.js do rede-amil-bradesco com links absolutos e a aba 'SulAmérica Adesão'."""
    js = (MODELO_DIR / "operadoras.js").read_text(encoding="utf-8")
    js = troca(js, '{ id: "sulamerica", nome: "SulAmérica", longo: " Saúde" },',
               '{ id: "sulamerica", nome: "SulAmérica", longo: " PME" },\n'
               '    { id: "sulamerica-adesao", nome: "SulAmérica Adesão", url: "' + SITE + '" },')
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
    print(f"index.html: {len(D['pr'])} hospitais em {len(D['cid'])} cidades / {len(D['uf'])} UFs, "
          f"{(RAIZ / 'index.html').stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
