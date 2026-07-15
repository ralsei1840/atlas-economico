# 🌍 Atlas Econômico Mundial

App em Python que baixa dados reais do [Banco Mundial](https://data.worldbank.org/) (200+ países desde 1960) e gera um painel interativo no navegador:

- **Mapa mundial** colorido do vermelho (pior) ao verde (melhor) por indicador e ano, com slider de tempo
- **Gráfico de linha** para comparar a evolução histórica de vários países

## Indicadores

PIB total, PIB per capita, RNB per capita, população, inflação anual, expectativa de vida, índice de Gini e IDH. Para inflação e Gini a escala de cores é invertida (menor = mais verde).

O IDH vem do PNUD/ONU (via [Our World in Data](https://ourworldindata.org/human-development-index)); os demais, da API do Banco Mundial.

## Como usar

```bash
pip install requests
python3 atlas.py
```

Na primeira execução ele baixa os dados (1–2 min) e salva um cache local — depois disso abre na hora e funciona offline. Para atualizar os dados:

```bash
python3 atlas.py --atualizar
```

O app gerado (`atlas.html`) abre automaticamente no navegador.

## Como funciona

O script consulta a API pública do Banco Mundial, embute os dados e o Plotly.js num único arquivo HTML e abre no navegador. Sem servidor, sem frameworks — só Python + `requests`.
