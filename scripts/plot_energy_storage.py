# pip install plotly==5.13.0
import plotly.express as px
import pandas as pd
import numpy as np
import yaml
from add_electricity import calculate_annuity
from _helpers import (
    add_storage_col_to_costs,
    nested_storage_dict,
)


if __name__ == "__main__":

    years = [2020, 2025, 2030, 2035, 2040, 2045, 2050]
    df_storage = pd.DataFrame()
    df = pd.DataFrame()

    for year in years:
        tech_cost_path = f"resources/costs_{year}.csv"
        with open("config.yaml", "r") as stream:
            try:
                config = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

        costs = pd.read_csv(tech_cost_path, index_col=["technology", "parameter"]).sort_index()
        costs = costs.value.unstack().fillna(config["costs"]["fill_values"])
        costs["capital_cost"] = (
            (
                calculate_annuity(costs["lifetime"], costs["discount rate"])
                + costs["FOM"] / 100.0
            )
            * costs["investment"]
            * 1
        )

        storage_meta_dict, storage_techs = nested_storage_dict(tech_cost_path)
        costs = add_storage_col_to_costs(costs, storage_meta_dict, storage_techs)
        storage_costs = costs.loc[~costs["type"].isna(),:]

        ### Data cleaning/preparation
        storage_costs = storage_costs.reset_index()
        storage_costs["technology"] = [str.replace("-bicharger","") for str in storage_costs["technology"]]
        storage_costs["technology"] = [str.replace("-charger","") for str in storage_costs["technology"]]
        storage_costs["technology"] = [str.replace("-discharger","") for str in storage_costs["technology"]]
        storage_costs["technology"] = [str.replace("-store","") for str in storage_costs["technology"]]
        storage_costs = storage_costs[["technology", "carrier", "type", "technology_type", "efficiency", "capital_cost", "investment"]]
        storage_costs[["capital_cost", "investment"]] /= 1000 # convet from  €/MWh -> €/kWh, €/MW -> €/kW
        
        # Fill empty dataframe
        # columns X-Charger capital costs [EUR/kW], Y-Discharger capital costs [EUR/kW], Z-Store capital costs [EUR/kWh], size-efficiency, color-type, symbol-technology, 

        for c in storage_costs["carrier"].unique():
            tech_type = storage_costs.technology_type
            carrier = storage_costs.carrier
            store_filter = (carrier == c) & (tech_type == "store")
            charger_or_bicharger_filter = (carrier == c) & ((tech_type == "charger") | (tech_type == "bicharger"))
            discharger_or_bicharger_filter = (carrier == c) & ((tech_type == "discharger") | (tech_type == "bicharger"))
            if (storage_costs.loc[discharger_or_bicharger_filter].technology_type.item()== "bicharger"):
                full_or_half_costs_discharger_cc = float(storage_costs.loc[discharger_or_bicharger_filter, "capital_cost"])/2
                full_or_half_costs_discharger_ic = float(storage_costs.loc[discharger_or_bicharger_filter, "investment"])/2
            else:
                full_or_half_costs_discharger_cc = float(storage_costs.loc[discharger_or_bicharger_filter, "capital_cost"])
                full_or_half_costs_discharger_ic = float(storage_costs.loc[discharger_or_bicharger_filter, "investment"])
            
            if (storage_costs.loc[charger_or_bicharger_filter].technology_type.item()== "bicharger"):
                full_or_half_costs_charger_cc = float(storage_costs.loc[charger_or_bicharger_filter, "capital_cost"])/2
                full_or_half_costs_charger_ic = float(storage_costs.loc[charger_or_bicharger_filter, "investment"])/2
            else:
                full_or_half_costs_charger_cc = float(storage_costs.loc[charger_or_bicharger_filter, "capital_cost"])
                full_or_half_costs_charger_ic = float(storage_costs.loc[charger_or_bicharger_filter, "investment"])

            df["technology"] = storage_costs.loc[storage_costs.carrier==c, "technology"].unique()
            df["type"] = storage_costs.loc[storage_costs.carrier==c,"type"].unique()
            df["Charger [EUR/kW]_cc"] = full_or_half_costs_charger_cc
            df["Charger [EUR/kW]_ic"] = full_or_half_costs_charger_ic
            df["Discharger [EUR/kW]_cc"] = full_or_half_costs_discharger_cc
            df["Discharger [EUR/kW]_ic"] = full_or_half_costs_discharger_ic
            df["Store [EUR/kWh]_cc"] = float(storage_costs.loc[store_filter, "capital_cost"])
            df["Store [EUR/kWh]_ic"] = float(storage_costs.loc[store_filter, "investment"])
            df["efficiency"] = np.prod(storage_costs.loc[storage_costs.carrier==c, "efficiency"])
            df["year"] = year
            df_storage = pd.concat([df_storage, df])

    df_storage = df_storage.reset_index().drop("index",axis=1)
    df_storage.to_csv("resources/energy_storage_costs.csv", index=False)
    fig = px.scatter_3d(
        df_storage,
        x='Charger [EUR/kW]_cc',
        y='Discharger [EUR/kW]_cc',
        z='Store [EUR/kWh]_cc',
        size='efficiency',
        color='type',
        symbol='technology',
        hover_data=['year'])
    fig.show()