# Radar Value — Points Radar v2.4 Role Opportunity Experiment

Cel: przetestować niszę Radar Value: **mniej istotni gracze, których rola rośnie po wypadnięciu ważnego teammate'a**.

To NIE korzysta z przyszłych danych ani z wyniku targetowego meczu przy tworzeniu sygnału.
Przed meczem używa tylko tego, co było widoczne wcześniej:
- ważny teammate nie zagrał w poprzednim meczu drużyny,
- kandydat miał normalnie maks. ok. 28 minut,
- w poprzednim meczu dostał wyraźny skok minut,
- opcjonalnie wzrosły FGA,
- powstaje Opportunity Score 0-100.

UWAGA: brak teammate'a w boxscore to proxy, a nie oficjalny historyczny injury report. Może oznaczać injury/rest/trade/DNP. To test mechanizmu rotacji.

## Uruchomienie

W PowerShell w folderze:

```powershell
pip install -r requirements.txt
python backtest_role_opportunity.py --season "2025-26"
```

Bardziej selektywny test:

```powershell
python backtest_role_opportunity.py --season "2025-26" --min-score 60 --max-baseline-min 26
```

## Co dostaniesz

- porównanie Points Radar v2.1 vs eksperymentalny v2.4 tylko na Role Opportunity subset,
- średnią realną zmianę minut,
- % przypadków, gdzie gracz utrzymał +5 minut,
- % przypadków, gdzie zdobył więcej punktów niż wcześniejsze L10,
- wyniki według Opportunity Score 50-59 / 60-69 / ...,
- `points_v24_role_opportunity_rows.csv`,
- `points_v24_opportunity_bands.csv`.

Nie uznajemy v2.4 za nowy champion tylko dlatego, że powstał. Najpierw patrzymy na sample size, persistence minut i MAE na subset.
