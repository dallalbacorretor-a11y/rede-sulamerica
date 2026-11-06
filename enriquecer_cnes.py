# Completa nome, endereço e telefone de cada estabelecimento pela API pública do CNES
# (apidadosabertos.saude.gov.br) e o nome do município pelo IBGE. Guarda cache local.
import csv, json, os, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

AQUI = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(AQUI, "cache_cnes.json")
MUN = os.path.join(AQUI, "municipios_ibge.json")
UA = {"User-Agent": "rede-sulamerica-mazza/1.0"}

def get(url, tent=4):
    for i in range(tent):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404: return None
            time.sleep(2 * (i + 1))
        except Exception:
            time.sleep(2 * (i + 1))
    return "ERRO"

if not os.path.exists(MUN):
    m = get("https://servicodados.ibge.gov.br/api/v1/localidades/municipios")
    json.dump({str(x["id"])[:6]: x["nome"] for x in m}, open(MUN, "w", encoding="utf-8"), ensure_ascii=False)
print("municípios IBGE:", len(json.load(open(MUN, encoding="utf-8"))))

rows = list(csv.DictReader(open(os.path.join(AQUI, "rede_hospitalar_sulamerica.csv"), encoding="utf-8-sig"), delimiter=";"))
cnes = sorted({re.sub(r"\D", "", r["CD_CNES"]) for r in rows} - {""})
cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
falta = [c for c in cnes if cache.get(c) in (None, "ERRO") and c not in cache or cache.get(c) == "ERRO"]
print(len(cnes), "CNES ·", len(falta), "a buscar")

CAMPOS = ["nome_fantasia", "nome_razao_social", "endereco_estabelecimento", "numero_estabelecimento",
          "bairro_estabelecimento", "codigo_cep_estabelecimento", "numero_telefone_estabelecimento",
          "latitude_estabelecimento_decimo_grau", "longitude_estabelecimento_decimo_grau",
          "estabelecimento_possui_centro_obstetrico", "estabelecimento_possui_centro_neonatal",
          "descricao_turno_atendimento", "codigo_municipio"]
def um(c):
    d = get(f"https://apidadosabertos.saude.gov.br/cnes/estabelecimentos/{int(c)}")
    return c, (d if d in (None, "ERRO") else {k: d.get(k) for k in CAMPOS})

feitos = 0
with ThreadPoolExecutor(6) as ex:
    for c, d in ex.map(um, falta):
        cache[c] = d; feitos += 1
        if feitos % 100 == 0:
            json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
            print(f"  {feitos}/{len(falta)}", flush=True)
json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
ok = sum(1 for c in cnes if isinstance(cache.get(c), dict))
print(f"pronto: {ok}/{len(cnes)} com dados do CNES · {sum(1 for c in cnes if cache.get(c) is None)} não encontrados · "
      f"{sum(1 for c in cnes if cache.get(c) == 'ERRO')} com erro")
