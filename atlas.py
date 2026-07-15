#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌍 Atlas Econômico Mundial
Baixa dados reais do Banco Mundial (200+ países desde 1960), gera um app
interativo com MAPA (verde = melhor, vermelho = pior) e GRÁFICO DE LINHA
para comparar países, e abre tudo no seu navegador.

Uso:
    pip install requests      (só na primeira vez)
    python3 atlas.py

Na primeira execução ele baixa os dados (1-2 min) e salva um cache.
Nas próximas, abre na hora. Para atualizar os dados: python3 atlas.py --atualizar
"""

import json
import os
import sys
import webbrowser

try:
    import requests
except ImportError:
    sys.exit("Falta a biblioteca 'requests'. Instale com:  pip install requests")

API = "https://api.worldbank.org/v2"
PLOTLY_URL = "https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.27.0/plotly.min.js"
# IDH é da ONU (PNUD), não do Banco Mundial — vem do Our World in Data
IDH_URL = "https://ourworldindata.org/grapher/human-development-index.csv"
AQUI = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(AQUI, "dados_banco_mundial.json")
SAIDA = os.path.join(AQUI, "atlas.html")

# nome: (código no Banco Mundial, maior é melhor?, usar escala log?)
INDICADORES = {
    "PIB total (US$)":            ("NY.GDP.MKTP.CD", True,  True),
    "PIB per capita (US$)":       ("NY.GDP.PCAP.CD", True,  True),
    "RNB per capita (US$)":       ("NY.GNP.PCAP.CD", True,  True),
    "População":                  ("SP.POP.TOTL",    True,  True),
    "Inflação anual (%)":         ("FP.CPI.TOTL.ZG", False, False),
    "Expectativa de vida (anos)": ("SP.DYN.LE00.IN", True,  False),
    "Índice de Gini":             ("SI.POV.GINI",    False, False),
    "IDH (0 a 1)":                ("IDH",            True,  False),
}


def baixar_paises():
    r = requests.get(f"{API}/country", params={"format": "json", "per_page": 400}, timeout=60)
    r.raise_for_status()
    return {
        p["id"]: p["name"]
        for p in r.json()[1]
        if p["region"]["value"] != "Aggregates"
    }


def baixar_indicador(codigo, paises):
    """Retorna {iso3: [[ano, valor], ...]} com todos os anos disponíveis."""
    series = {}
    pagina, paginas = 1, 1
    while pagina <= paginas:
        r = requests.get(
            f"{API}/country/all/indicator/{codigo}",
            params={"format": "json", "per_page": 10000, "page": pagina},
            timeout=120,
        )
        r.raise_for_status()
        js = r.json()
        paginas = js[0]["pages"]
        for linha in js[1] or []:
            iso3 = linha.get("countryiso3code")
            if linha["value"] is None or iso3 not in paises:
                continue
            series.setdefault(iso3, []).append([int(linha["date"]), linha["value"]])
        pagina += 1
    for iso3 in series:
        series[iso3].sort()
    return series


def baixar_idh(paises):
    """IDH (PNUD/ONU) via Our World in Data, com todos os anos desde 1990."""
    import csv
    import io
    r = requests.get(IDH_URL, timeout=120, headers={"User-Agent": "atlas-economico"})
    r.raise_for_status()
    series = {}
    for linha in csv.DictReader(io.StringIO(r.text)):
        iso3 = linha.get("Code", "")
        valor = linha.get("Human Development Index", "")
        if iso3 in paises and valor:
            series.setdefault(iso3, []).append([int(linha["Year"]), float(valor)])
    for iso3 in series:
        series[iso3].sort()
    return series


def baixar_tudo():
    print("Baixando lista de países...")
    paises = baixar_paises()
    print(f"  {len(paises)} países encontrados.")
    dados = {}
    for i, (nome, (codigo, _, _)) in enumerate(INDICADORES.items(), 1):
        print(f"Baixando {i}/{len(INDICADORES)}: {nome} ...")
        dados[codigo] = baixar_idh(paises) if codigo == "IDH" else baixar_indicador(codigo, paises)
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump({"paises": paises, "dados": dados}, f)
    print(f"Cache salvo em {CACHE}")
    return paises, dados


def obter_plotly():
    """Baixa o plotly.js uma vez e guarda ao lado do script (app fica 100% offline)."""
    caminho = os.path.join(AQUI, "plotly.min.js")
    if not os.path.exists(caminho):
        print("Baixando biblioteca de gráficos (plotly.js, ~4 MB)...")
        r = requests.get(PLOTLY_URL, timeout=120)
        r.raise_for_status()
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(r.text)
    with open(caminho, encoding="utf-8") as f:
        return f.read()


MODELO_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>🌍 Atlas Econômico Mundial</title>
<script>__PLOTLY__</script>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; }
  header { padding: 16px 28px; background: #1e293b; border-bottom: 1px solid #334155; }
  header h1 { margin: 0; font-size: 22px; }
  header p { margin: 4px 0 0; color: #94a3b8; font-size: 13px; }
  .controls { display: flex; flex-wrap: wrap; gap: 18px; padding: 14px 28px; background: #16213a; align-items: flex-start; }
  .controls label { font-size: 13px; color: #94a3b8; display: block; margin-bottom: 4px; }
  select, input[type=range] { background: #1e293b; color: #e2e8f0; border: 1px solid #334155; border-radius: 8px; padding: 7px 10px; font-size: 14px; }
  select[multiple] { min-width: 230px; height: 108px; }
  .tabs { display: flex; gap: 8px; padding: 12px 28px 0; }
  .tab { padding: 9px 18px; border-radius: 10px 10px 0 0; background: #1e293b; cursor: pointer; border: 1px solid #334155; border-bottom: none; font-size: 14px; user-select: none; }
  .tab.active { background: #2563eb; border-color: #2563eb; color: #fff; }
  .panel { display: none; padding: 10px 28px 28px; }
  .panel.active { display: block; }
  #mapa, #linhas { width: 100%; height: 66vh; background: #1e293b; border-radius: 12px; }
  #status { padding: 4px 28px; font-size: 13px; color: #94a3b8; min-height: 20px; }
  .anoval { font-weight: bold; color: #e2e8f0; }
</style>
</head>
<body>
<header>
  <h1>🌍 Atlas Econômico Mundial</h1>
  <p>Banco Mundial · 200+ países desde 1960 · <b style="color:#4ade80">verde = melhor</b> · <b style="color:#f87171">vermelho = pior</b> (escala invertida p/ inflação e Gini)</p>
</header>

<div class="controls">
  <div>
    <label>Indicador</label>
    <select id="indicador"></select>
  </div>
  <div>
    <label>Ano do mapa: <span class="anoval" id="anoval">2023</span></label>
    <input type="range" id="ano" min="1960" max="2025" value="2023" style="width:230px">
  </div>
  <div>
    <label>Países do gráfico de linha (Ctrl+clique p/ vários)</label>
    <select id="paises" multiple></select>
  </div>
</div>

<div class="tabs">
  <div class="tab active" data-p="pmapa">🗺️ Mapa mundial</div>
  <div class="tab" data-p="plinhas">📈 Comparação histórica</div>
</div>
<div id="status"></div>
<div class="panel active" id="pmapa"><div id="mapa"></div></div>
<div class="panel" id="plinhas"><div id="linhas"></div></div>

<script>
const PAISES = __PAISES__;      // {ISO3: nome}
const DADOS  = __DADOS__;       // {codigo: {ISO3: [[ano, valor], ...]}}
const INDICADORES = __INDICADORES__;  // {nome: [codigo, maiorMelhor, log]}

const $ = id => document.getElementById(id);
const fmt = v => v.toLocaleString("pt-BR", { maximumFractionDigits: 2 });

// escala vermelho→amarelo→verde (o plotly.js não tem "RdYlGn" nativo)
const RDYLGN = [
  [0.0, "#a50026"], [0.1, "#d73027"], [0.2, "#f46d43"], [0.3, "#fdae61"],
  [0.4, "#fee08b"], [0.5, "#ffffbf"], [0.6, "#d9ef8b"], [0.7, "#a6d96a"],
  [0.8, "#66bd63"], [0.9, "#1a9850"], [1.0, "#006837"],
];

// abrevia números grandes: 1,5 tri / 300 bi / 12 mi / 850 mil
function abrevia(v) {
  const abs = Math.abs(v);
  if (abs >= 1e12) return fmt(v / 1e12) + " tri";
  if (abs >= 1e9)  return fmt(v / 1e9)  + " bi";
  if (abs >= 1e6)  return fmt(v / 1e6)  + " mi";
  if (abs >= 1e3)  return fmt(v / 1e3)  + " mil";
  return fmt(v);
}

// percentil simples para cortar valores extremos da escala de cores
function percentil(arr, p) {
  const s = [...arr].sort((a, b) => a - b);
  return s[Math.round(p * (s.length - 1))];
}

// valor mais recente do país até o ano escolhido (janela de 6 anos)
function valorNoAno(serie, ano) {
  let achado = null;
  for (const [a, v] of serie) {
    if (a > ano) break;
    if (a >= ano - 5) achado = [a, v];
  }
  return achado;
}

function desenhaMapa() {
  const nome = $("indicador").value;
  const [codigo, maiorMelhor, usaLog] = INDICADORES[nome];
  const ano = +$("ano").value;
  const locs = [], vals = [], hovers = [];
  for (const [iso3, serie] of Object.entries(DADOS[codigo] || {})) {
    const achado = valorNoAno(serie, ano);
    if (!achado) continue;
    const [a, v] = achado;
    locs.push(iso3);
    vals.push(usaLog ? Math.log10(Math.max(v, 1)) : v);
    hovers.push(`<b>${PAISES[iso3] || iso3}</b><br>${nome}: ${usaLog ? abrevia(v) : fmt(v)}<br>Ano do dado: ${a}`);
  }
  // corta os 2% extremos p/ outliers não achatarem as cores dos demais países
  const zmin = percentil(vals, 0.02), zmax = percentil(vals, 0.98);

  // colorbar legível: na escala log mostra 1 mi, 1 bi, 1 tri em vez do expoente
  const colorbar = { title: { text: nome, font: { color: "#e2e8f0", size: 11 } }, tickfont: { color: "#94a3b8" } };
  if (usaLog) {
    const tv = [];
    for (let e = Math.ceil(zmin); e <= Math.floor(zmax); e++) tv.push(e);
    colorbar.tickvals = tv;
    colorbar.ticktext = tv.map(e => abrevia(Math.pow(10, e)));
  }

  Plotly.react("mapa", [{
    type: "choropleth", locations: locs, z: vals, text: hovers,
    hovertemplate: "%{text}<extra></extra>",
    colorscale: RDYLGN, reversescale: !maiorMelhor,
    zmin: zmin, zmax: zmax,
    colorbar: colorbar,
    marker: { line: { color: "#0f172a", width: 0.4 } },
  }], {
    geo: { projection: { type: "natural earth" }, bgcolor: "rgba(0,0,0,0)", showframe: false, landcolor: "#1e293b", coastlinecolor: "#334155" },
    paper_bgcolor: "rgba(0,0,0,0)", font: { color: "#e2e8f0" },
    margin: { l: 0, r: 0, t: 42, b: 0 },
    title: { text: `${nome} — ${ano}`, font: { size: 15 } },
  }, { responsive: true });
  $("status").textContent = `${locs.length} países com dados para ${nome} em ${ano} (usa o dado mais recente até 5 anos antes).`;
}

function desenhaLinhas() {
  const nome = $("indicador").value;
  const [codigo, , usaLog] = INDICADORES[nome];
  const sel = [...$("paises").selectedOptions].map(o => o.value);
  if (!sel.length) { $("status").textContent = "Selecione países acima (Ctrl+clique)."; return; }
  const traces = sel.map(iso3 => {
    const serie = (DADOS[codigo] || {})[iso3] || [];
    return {
      x: serie.map(p => p[0]), y: serie.map(p => p[1]),
      mode: "lines", name: PAISES[iso3] || iso3,
      hovertemplate: "%{y:,.2f}<extra>" + (PAISES[iso3] || iso3) + "</extra>",
    };
  });
  Plotly.react("linhas", traces, {
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: "#e2e8f0" }, hovermode: "x unified",
    title: { text: `${nome} — evolução histórica`, font: { size: 15 } },
    xaxis: { title: "Ano", gridcolor: "#334155" },
    yaxis: { title: nome, gridcolor: "#334155", type: usaLog ? "log" : "linear" },
    margin: { l: 75, r: 20, t: 45, b: 50 },
    legend: { orientation: "h", y: -0.16 },
  }, { responsive: true });
  $("status").textContent = "";
}

function atualiza() {
  if ($("pmapa").classList.contains("active")) desenhaMapa(); else desenhaLinhas();
}

// ---- inicialização
for (const n of Object.keys(INDICADORES)) {
  const o = document.createElement("option");
  o.value = n; o.textContent = n;
  $("indicador").appendChild(o);
}
$("indicador").value = "PIB per capita (US$)";

const selPaises = $("paises");
Object.entries(PAISES)
  .sort((a, b) => a[1].localeCompare(b[1]))
  .forEach(([iso3, nomeP]) => {
    const o = document.createElement("option");
    o.value = iso3; o.textContent = nomeP;
    if (["BRA", "USA", "CHN", "DEU", "JPN"].includes(iso3)) o.selected = true;
    selPaises.appendChild(o);
  });

$("indicador").onchange = atualiza;
$("ano").oninput = () => { $("anoval").textContent = $("ano").value; };
$("ano").onchange = desenhaMapa;
selPaises.onchange = () => { if ($("plinhas").classList.contains("active")) desenhaLinhas(); };

document.querySelectorAll(".tab").forEach(t => t.onclick = () => {
  document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
  document.querySelectorAll(".panel").forEach(x => x.classList.remove("active"));
  t.classList.add("active");
  $(t.dataset.p).classList.add("active");
  atualiza();
});

desenhaMapa();
</script>
</body>
</html>
"""


def gerar_html(paises, dados, plotly_js):
    meta = {nome: list(v) for nome, v in INDICADORES.items()}
    html = (
        MODELO_HTML
        .replace("__PLOTLY__", plotly_js)
        .replace("__PAISES__", json.dumps(paises, ensure_ascii=False))
        .replace("__DADOS__", json.dumps(dados))
        .replace("__INDICADORES__", json.dumps(meta, ensure_ascii=False))
    )
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write(html)
    return SAIDA


def main():
    atualizar = "--atualizar" in sys.argv
    if os.path.exists(CACHE) and not atualizar:
        print("Usando cache de dados (para atualizar: python3 atlas.py --atualizar)")
        with open(CACHE, encoding="utf-8") as f:
            c = json.load(f)
        paises, dados = c["paises"], c["dados"]
    else:
        try:
            paises, dados = baixar_tudo()
        except requests.RequestException as e:
            sys.exit(f"Erro de conexão com o Banco Mundial: {e}\nVerifique sua internet e tente de novo.")
    plotly_js = obter_plotly()
    caminho = gerar_html(paises, dados, plotly_js)
    print(f"App gerado: {caminho}")
    print("Abrindo no navegador...")
    webbrowser.open("file://" + caminho)


if __name__ == "__main__":
    main()
