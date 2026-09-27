import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell
def _():
    from itertools import combinations

    import altair as alt
    import marimo as mo
    import pandas as pd
    from scipy.stats import kendalltau, weightedtau

    alt.renderers.set_embed_options(renderer="svg")
    return alt, combinations, kendalltau, mo, pd, weightedtau


@app.cell(hide_code=True)
def _():
    # all the datasets!

    configs = {
        # MOVIELENS
        "ML100K": {
            "category": "MovieLens",
            "path": "movielens/ML100K/run-summary.csv",
            "where": "part = 0",
        },
        "ML1M": {
            "category": "MovieLens",
            "path": "movielens/ML1M/run-summary.csv",
            "where": "part = 0",
        },
        "ML10M": {
            "category": "MovieLens",
            "path": "movielens/ML10M/run-summary.csv",
            "where": "part = 'valid'",
        },
        "ML20M": {
            "category": "MovieLens",
            "path": "movielens/ML20M/run-summary.csv",
            "where": "part = 'valid'",
        },
        "ML25M": {
            "category": "MovieLens",
            "path": "movielens/ML25M/run-summary.csv",
            "where": "part = 'valid'",
        },
        "ML32M": {
            "category": "MovieLens",
            "path": "movielens/ML32M/run-summary.csv",
            "where": "part = 'valid'",
        },
        # AMAZON
        "AmazonAuto": {
            "category": "Amazon",
            "path": "amazon/2023-5core/Auto/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonBaby": {
            "category": "Amazon",
            "path": "amazon/2023-5core/Baby/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonBeauty": {
            "category": "Amazon",
            "path": "amazon/2023-5core/Beauty/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonBooks": {
            "category": "Amazon",
            "path": "amazon/2023-5core/Books/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonCDV": {
            "category": "Amazon",
            "path": "amazon/2023-5core/CDV/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonCell": {
            "category": "Amazon",
            "path": "amazon/2023-5core/Cell/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonClothing": {
            "category": "Amazon",
            "path": "amazon/2023-5core/Clothing//run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonCrafts": {
            "category": "Amazon",
            "path": "amazon/2023-5core/Crafts/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonElec": {
            "category": "Amazon",
            "path": "amazon/2023-5core/Elec/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonGrocery": {
            "category": "Amazon",
            "path": "amazon/2023-5core/Grocery/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonHealthHouse": {
            "category": "Amazon",
            "path": "amazon/2023-5core/HealthHouse/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonHomeKitchen": {
            "category": "Amazon",
            "path": "amazon/2023-5core/HealthHouse/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonIndSci": {
            "category": "Amazon",
            "path": "amazon/2023-5core/IndSci/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonKindle": {
            "category": "Amazon",
            "path": "amazon/2023-5core/Kindle/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonMovTV": {
            "category": "Amazon",
            "path": "amazon/2023-5core/MovTV/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonMusInst": {
            "category": "Amazon",
            "path": "amazon/2023-5core/MusInst/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonOffice": {
            "category": "Amazon",
            "path": "amazon/2023-5core/Office/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonPet": {
            "category": "Amazon",
            "path": "amazon/2023-5core/Pet/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonPLG": {
            "category": "Amazon",
            "path": "amazon/2023-5core/PLG/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonSoftware": {
            "category": "Amazon",
            "path": "amazon/2023-5core/Software/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonSports": {
            "category": "Amazon",
            "path": "amazon/2023-5core/Sports/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonTHI": {
            "category": "Amazon",
            "path": "amazon/2023-5core/THI/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonToys": {
            "category": "Amazon",
            "path": "amazon/2023-5core/Toys/run-summary.csv",
            "where": "part = 'valid'",
        },
        "AmazonVidGames": {
            "category": "Amazon",
            "path": "amazon/2023-5core/VidGames/run-summary.csv",
            "where": "part = 'valid'",
        },
        # STEAM
        "SteamAustralia": {
            "category": "Steam",
            "path": "steam/australia/run-summary.csv",
            "where": "part = 'tune'",
        },
    }
    return (configs,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Datasets Sorting**
    """)
    return


@app.cell(hide_code=True)
def _(configs, mo):
    dataset_selector = mo.ui.dropdown(
        options=list(configs.keys()),
        value="ML100K",
        label="Dataset:",
    )

    sort_selector = mo.ui.radio(options=["RBP", "NDCG"], value="RBP", label="Rank by:", inline=True)

    mo.hstack(
        [dataset_selector, sort_selector],
        justify="start",
        gap=10,
        align="center",
    )
    return dataset_selector, sort_selector


@app.cell(hide_code=True)
def _(configs, dataset_selector, mo, sort_selector):
    dataset = dataset_selector.value
    sort_metric = sort_selector.value

    # first, pull out a dataset from the dictionary of datasets AKA configs
    config = configs[dataset]
    # take the file path
    file_path = config["path"]
    # take the part (valid, 0, test, etc.)
    part_value = config["where"]

    sorted_datasets = mo.sql(
        f"""
        SELECT
            model,
            variant,
            round(RBP, 3) AS RBP,
            round(NDCG, 3) AS NDCG,
            RANK() OVER (ORDER BY {sort_metric} DESC) AS rank
        FROM read_csv('{file_path}')
        WHERE {part_value}
        GROUP BY model, variant, RBP, NDCG
        ORDER BY rank
        """
    )

    mo.vstack(
        [
            mo.md(f"**{dataset} Sorted by {sort_metric}**"),
            sorted_datasets,
        ]
    )
    return config, dataset, sort_metric


@app.cell(hide_code=True)
def _(mo):
    selected_metric = mo.ui.radio(
        options=["RBP", "NDCG"],
        value="RBP",
        label="Metric:",
    )

    selected_metric
    return (selected_metric,)


@app.cell(hide_code=True)
def _(configs, mo, selected_metric):
    metric = selected_metric.value

    # empty list to hold the query for every dataset
    queries = []

    # retrieving data from configs dictionary of all datasets and then adding by for loop
    for _dataset_name, _config in configs.items():
        _file_path = _config["path"]
        _part_value = _config["where"]

        # base query
        query = f"""
            SELECT
                '{_dataset_name}' AS dataset,
                model,
                variant,
                RBP,
                NDCG,
                RANK() OVER (ORDER BY {metric} DESC) AS rank
            FROM read_csv('{_file_path}')
            WHERE {_part_value}
            """

        # add queries to list!
        queries.append(query)

    # add everything into one SQL string, so the final result is one dataframe
    full_sql = f"""
    WITH all_rankings AS (
        {" UNION ALL ".join(queries)}
    )
    SELECT dataset, model, variant, round(RBP, 3) AS RBP, round(NDCG, 3) AS NDCG
    FROM all_rankings

    /*select the top*/
    WHERE rank = 1
    """

    top_tracking = mo.sql(full_sql)

    mo.vstack(
        [
            mo.md(f"**Best Model-Variant Pair of Each Dataset by {metric}**"),
            top_tracking,
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Kendall's Tau-b**
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    tau_method_selector = mo.ui.radio(
        options=[
            "Non-weighted Kendall's tau-b",
            "Weighted Kendall's tau",
        ],
        value="Non-weighted Kendall's tau-b",
        label="Kendall's tau method:",
    )

    tau_sort_selector = mo.ui.radio(
        options=[
            "Keep dataset order",
            "Highest Kendall's tau first",
        ],
        value="Keep dataset order",
        label="Comparison order:",
    )

    mo.vstack(
        [
            tau_method_selector,
            tau_sort_selector,
        ]
    )
    return tau_method_selector, tau_sort_selector


@app.cell(hide_code=True)
def _(
    alt,
    combinations,
    configs,
    kendalltau,
    mo,
    pd,
    tau_method_selector,
    tau_sort_selector,
    weightedtau,
):
    _tau_method = tau_method_selector.value
    _sort_choice = tau_sort_selector.value

    _rankings = {}
    _rows = []

    # calculate RBP and NDCG rankings for every dataset
    for _name, _config in configs.items():
        _rankings[_name] = mo.sql(
            f"""
            SELECT
                model,
                variant,
                RANK() OVER (
                    ORDER BY RBP DESC
                ) AS RBP_rank,
                RANK() OVER (
                    ORDER BY NDCG DESC
                ) AS NDCG_rank
            FROM read_csv('{_config["path"]}')
            WHERE {_config["where"]}
            GROUP BY model, variant, RBP, NDCG
            """
        )

    # compare every dataset pair within the same category
    for _dataset_a, _dataset_b in combinations(
        configs.keys(),
        2,
    ):
        _category_a = configs[_dataset_a]["category"]
        _category_b = configs[_dataset_b]["category"]

        if _category_a != _category_b:
            continue

        # keep model-variant pairs found in both datasets
        _shared = pd.merge(
            _rankings[_dataset_a],
            _rankings[_dataset_b],
            on=["model", "variant"],
            how="inner",
            suffixes=("_a", "_b"),
        )

        if len(_shared) >= 2:
            if _tau_method == "Weighted Kendall's tau":
                # negate ranks so top-ranked pairs receive greater weight
                _rbp_result = weightedtau(
                    -_shared["RBP_rank_a"],
                    -_shared["RBP_rank_b"],
                )

                _ndcg_result = weightedtau(
                    -_shared["NDCG_rank_a"],
                    -_shared["NDCG_rank_b"],
                )
            else:
                _rbp_result = kendalltau(
                    _shared["RBP_rank_a"],
                    _shared["RBP_rank_b"],
                    variant="b",
                    nan_policy="omit",
                )

                _ndcg_result = kendalltau(
                    _shared["NDCG_rank_a"],
                    _shared["NDCG_rank_b"],
                    variant="b",
                    nan_policy="omit",
                )

            _rbp_tau = _rbp_result.statistic
            _ndcg_tau = _ndcg_result.statistic

        else:
            _rbp_tau = float("nan")
            _ndcg_tau = float("nan")

        _rows.append(
            {
                "category": _category_a,
                "dataset_a": _dataset_a,
                "dataset_b": _dataset_b,
                "comparison": f"{_dataset_a} to {_dataset_b}",
                "method": _tau_method,
                "RBP_tau": _rbp_tau,
                "NDCG_tau": _ndcg_tau,
                "n_items": len(_shared),
            }
        )

    # create the pairwise comparison table
    _pairwise_results = pd.DataFrame(
        _rows,
        columns=[
            "category",
            "dataset_a",
            "dataset_b",
            "comparison",
            "method",
            "RBP_tau",
            "NDCG_tau",
            "n_items",
        ],
    )

    # find the larger tau for optional sorting
    _pairwise_results["highest_tau"] = _pairwise_results[["RBP_tau", "NDCG_tau"]].max(axis=1)

    # sort comparisons only when requested
    if _sort_choice == "Highest Kendall's tau first":
        _pairwise_results = _pairwise_results.sort_values(
            "highest_tau",
            ascending=False,
            na_position="last",
        ).reset_index(drop=True)
    else:
        _pairwise_results = _pairwise_results.reset_index(drop=True)

    _pairwise_results = _pairwise_results.round(4)

    # calculate average RBP and NDCG tau for each category
    _results = _pairwise_results.groupby(
        "category",
        as_index=False,
        sort=False,
    ).agg(
        average_RBP_tau=("RBP_tau", "mean"),
        average_NDCG_tau=("NDCG_tau", "mean"),
        number_of_comparisons=("comparison", "count"),
        average_n_items=("n_items", "mean"),
    )

    # find the larger category average for optional sorting
    _results["highest_average_tau"] = _results[["average_RBP_tau", "average_NDCG_tau"]].max(axis=1)

    # sort category averages only when requested
    if _sort_choice == "Highest Kendall's tau first":
        _results = _results.sort_values(
            "highest_average_tau",
            ascending=False,
            na_position="last",
        ).reset_index(drop=True)
    else:
        _results = _results.reset_index(drop=True)

    _results = _results.round(4)
    _category_order = _results["category"].tolist()

    # reshape results so RBP and NDCG can appear together
    _chart_data = _results.melt(
        id_vars=[
            "category",
            "number_of_comparisons",
            "average_n_items",
        ],
        value_vars=[
            "average_RBP_tau",
            "average_NDCG_tau",
        ],
        var_name="metric",
        value_name="average_tau",
    )

    _chart_data["metric"] = _chart_data["metric"].map(
        {
            "average_RBP_tau": "RBP",
            "average_NDCG_tau": "NDCG",
        }
    )

    # create the grouped RBP and NDCG chart
    _chart = (
        alt.Chart(_chart_data)
        .mark_bar()
        .encode(
            x=alt.X(
                "category:N",
                title="Dataset category",
                sort=_category_order,
            ),
            xOffset=alt.XOffset(
                "metric:N",
                sort=["RBP", "NDCG"],
            ),
            y=alt.Y(
                "average_tau:Q",
                title="Average Kendall's tau",
                scale=alt.Scale(domain=[-1, 1]),
            ),
            color=alt.Color(
                "metric:N",
                title="Metric",
                scale=alt.Scale(
                    domain=["RBP", "NDCG"],
                    range=["#66deca", "#ed8cdf"],
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    "category:N",
                    title="Category",
                ),
                alt.Tooltip(
                    "metric:N",
                    title="Metric",
                ),
                alt.Tooltip(
                    "average_tau:Q",
                    title="Average tau",
                    format=".4f",
                ),
                alt.Tooltip(
                    "number_of_comparisons:Q",
                    title="Comparisons",
                ),
                alt.Tooltip(
                    "average_n_items:Q",
                    title="Average shared pairs",
                    format=".2f",
                ),
            ],
        )
        .properties(
            width=500,
            height=350,
            title=f"Within-Category Agreement: {_tau_method}",
        )
    )

    _note = (
        "Weighted Kendall's tau emphasizes agreement near the top of the rankings."
        if _tau_method == "Weighted Kendall's tau"
        else "Non-weighted Kendall's tau-b gives every ranking position equal importance."
    )

    mo.vstack(
        [
            mo.md(f"**Pairwise {_tau_method}**"),
            mo.md(_note),
            _pairwise_results,
            mo.md("**Average RBP and NDCG Agreement by Category**"),
            _results,
            _chart,
        ]
    )
    return


@app.cell(hide_code=True)
def _(configs, mo):
    top_pair_metric_selector = mo.ui.radio(
        options=["RBP", "NDCG"],
        value="RBP",
        label="Rank top model-variant pairs by:",
    )

    top_pair_common_selector = mo.ui.checkbox(
        value=False,
        label="Only include pairs present in every dataset",
    )

    top_pair_category_options = ["ALL"] + sorted(
        {config["category"] for config in configs.values()}
    )

    top_pair_category_selector = mo.ui.dropdown(
        options=top_pair_category_options,
        value="ALL",
        label="Choose dataset category:",
    )

    mo.vstack(
        [
            top_pair_metric_selector,
            top_pair_common_selector,
            top_pair_category_selector,
        ]
    )
    return (
        top_pair_category_selector,
        top_pair_common_selector,
        top_pair_metric_selector,
    )


@app.cell(hide_code=True)
def _(
    alt,
    configs,
    mo,
    pd,
    top_pair_category_selector,
    top_pair_common_selector,
    top_pair_metric_selector,
):
    _metric = top_pair_metric_selector.value
    _only_common = top_pair_common_selector.value
    _selected_category = top_pair_category_selector.value

    _other_metric = "NDCG" if _metric == "RBP" else "RBP"

    # limit the analysis to the selected category
    if _selected_category == "ALL":
        _selected_configs = configs
        _selected_title = "All Dataset Categories"
    else:
        _selected_configs = {
            _name: _config
            for _name, _config in configs.items()
            if _config["category"] == _selected_category
        }
        _selected_title = _selected_category

    _frames = []

    # load RBP and NDCG for every selected dataset
    for _dataset_name, _config in _selected_configs.items():
        _frame = mo.sql(
            f"""
            SELECT
                model,
                variant,
                AVG(RBP) AS RBP,
                AVG(NDCG) AS NDCG
            FROM read_csv('{_config["path"]}')
            WHERE {_config["where"]}
            GROUP BY model, variant
            """
        )

        _frame = _frame.copy()
        _frame["dataset"] = _dataset_name
        _frame["category"] = _config["category"]

        _frames.append(_frame)

    # combine all selected datasets
    _all_results = pd.concat(
        _frames,
        ignore_index=True,
    )

    # count how many selected datasets contain each pair
    _pair_counts = _all_results.groupby(
        ["model", "variant"],
        as_index=False,
    ).agg(
        dataset_count=("dataset", "nunique"),
    )

    # find pairs present in every selected dataset
    _common_pairs = _pair_counts[_pair_counts["dataset_count"] == len(_selected_configs)][
        ["model", "variant"]
    ].reset_index(drop=True)

    # apply the common-pair filter before ranking
    if _only_common:
        _filtered_results = pd.merge(
            _all_results,
            _common_pairs,
            on=["model", "variant"],
            how="inner",
        )
    else:
        _filtered_results = _all_results.copy().reset_index(drop=True)

    _metric_totals = []

    # calculate top-three points separately for RBP and NDCG
    for _ranking_metric in ["RBP", "NDCG"]:
        _ranked = _filtered_results.sort_values(
            [
                "dataset",
                _ranking_metric,
                "model",
                "variant",
            ],
            ascending=[True, False, True, True],
        ).reset_index(drop=True)

        # assign ranks starting at one within each dataset
        _ranked["top_rank"] = _ranked.groupby("dataset").cumcount() + 1

        # keep the top three pairs from each dataset
        _metric_points = _ranked[_ranked["top_rank"] <= 3].copy().reset_index(drop=True)

        # award weighted points based on rank
        _metric_points["points"] = _metric_points["top_rank"].map(
            {
                1: 1.0,
                2: 2 / 3,
                3: 1 / 3,
            }
        )

        _metric_points["score"] = _metric_points[_ranking_metric]

        # calculate totals for the current metric
        _totals = (
            _metric_points.groupby(
                ["model", "variant"],
                as_index=False,
            )
            .agg(
                total_points=("points", "sum"),
                times_in_top_3=("dataset", "nunique"),
                average_metric_score=("score", "mean"),
            )
            .sort_values(
                [
                    "total_points",
                    "times_in_top_3",
                    "average_metric_score",
                ],
                ascending=[False, False, False],
            )
            .reset_index(drop=True)
        )

        _totals["metric"] = _ranking_metric
        _metric_totals.append(_totals)

    # combine the RBP and NDCG point totals
    _all_metric_totals = pd.concat(
        _metric_totals,
        ignore_index=True,
    )

    # choose the displayed pairs using the selected metric
    _primary_points = (
        _all_metric_totals[_all_metric_totals["metric"] == _metric]
        .sort_values(
            [
                "total_points",
                "times_in_top_3",
                "average_metric_score",
            ],
            ascending=[False, False, False],
        )
        .reset_index(drop=True)
    )

    _top_pairs = _primary_points.head(15)[["model", "variant"]].copy()

    _metric_names = pd.DataFrame(
        {
            "metric": [
                _metric,
                _other_metric,
            ]
        }
    )

    # create one RBP and one NDCG row for every displayed pair
    _chart_data = _top_pairs.merge(
        _metric_names,
        how="cross",
    ).merge(
        _all_metric_totals,
        on=["model", "variant", "metric"],
        how="left",
    )

    # use zero when a pair did not reach the top three
    _chart_data["total_points"] = _chart_data["total_points"].fillna(0)

    _chart_data["times_in_top_3"] = _chart_data["times_in_top_3"].fillna(0).astype(int)

    _chart_data["model_variant"] = _chart_data["model"] + " / " + _chart_data["variant"]

    # keep the chart sorted by the selected metric
    _pair_order = (
        _primary_points.head(15)
        .assign(model_variant=lambda _data: _data["model"] + " / " + _data["variant"])[
            "model_variant"
        ]
        .tolist()
    )

    # draw RBP and NDCG directly above and below each other
    _chart = (
        alt.Chart(_chart_data)
        .mark_bar()
        .encode(
            x=alt.X(
                "total_points:Q",
                title="Points",
            ),
            y=alt.Y(
                "model_variant:N",
                sort=_pair_order,
                title="Model-variant pair",
            ),
            yOffset=alt.YOffset(
                "metric:N",
                sort=[
                    _metric,
                    _other_metric,
                ],
            ),
            color=alt.Color(
                "metric:N",
                title="Metric",
                scale=alt.Scale(
                    domain=[
                        _metric,
                        _other_metric,
                    ],
                    range=[
                        "#DAEDEF",
                        "#9EC8CD",
                    ],
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    "model:N",
                    title="Model",
                ),
                alt.Tooltip(
                    "variant:N",
                    title="Variant",
                ),
                alt.Tooltip(
                    "metric:N",
                    title="Metric",
                ),
                alt.Tooltip(
                    "total_points:Q",
                    title="Points",
                    format=".3f",
                ),
                alt.Tooltip(
                    "average_metric_score:Q",
                    title="Average metric value",
                    format=".4f",
                ),
                alt.Tooltip(
                    "times_in_top_3:Q",
                    title="Times in top 3",
                ),
            ],
        )
        .properties(
            width=700,
            height=max(
                400,
                len(_pair_order) * 48,
            ),
            title=(f"Top Model-Variant Pairs: {_metric} and {_other_metric}"),
        )
    )

    # describe the active common-pair filter
    if _only_common:
        _common_text = (
            f"Only {len(_common_pairs)} model-variant pairs "
            f"present in all {len(_selected_configs)} "
            f"{_selected_title} datasets"
        )
    else:
        _common_text = (
            f"All available model-variant pairs across "
            f"{len(_selected_configs)} "
            f"{_selected_title} datasets"
        )

    mo.vstack(
        [
            mo.md(
                f"**Top Model-Variant Pairs: "
                f"{_selected_title}**  \n"
                f"Sorted by: **{_metric}**  \n"
                f"{_common_text}"
            ),
            _chart_data,
            _chart,
        ]
    )
    return


@app.cell(hide_code=True)
def _(configs, mo):
    category_compare_dataset_selector = mo.ui.dropdown(
        options=list(configs.keys()),
        value=list(configs.keys())[0],
        label="Dataset for average:",
    )

    category_compare_metric_selector = mo.ui.radio(
        options=["RBP", "NDCG"],
        value="RBP",
        label="Rank by:",
    )

    category_compare_tau_selector = mo.ui.radio(
        options=[
            "Non-weighted Kendall's tau-b",
            "Weighted Kendall's tau",
        ],
        value="Non-weighted Kendall's tau-b",
        label="Kendall's tau method:",
    )

    category_compare_scope_selector = mo.ui.radio(
        options=[
            "All datasets",
            "Within the same category",
            "Outside the category",
        ],
        value="All datasets",
        label="Comparison scope:",
    )

    mo.vstack(
        [
            category_compare_dataset_selector,
            category_compare_metric_selector,
            category_compare_tau_selector,
            category_compare_scope_selector,
        ]
    )
    return (
        category_compare_dataset_selector,
        category_compare_metric_selector,
        category_compare_scope_selector,
        category_compare_tau_selector,
    )


@app.cell(hide_code=True)
def _(
    alt,
    category_compare_dataset_selector,
    category_compare_metric_selector,
    category_compare_scope_selector,
    category_compare_tau_selector,
    configs,
    kendalltau,
    mo,
    pd,
    weightedtau,
):
    _selected_dataset = category_compare_dataset_selector.value
    _metric = category_compare_metric_selector.value
    _tau_method = category_compare_tau_selector.value
    _scope = category_compare_scope_selector.value

    _order = list(configs.keys())
    _rankings = {}

    # calculate rankings once for every dataset
    for _name, _config in configs.items():
        _rankings[_name] = mo.sql(
            f"""
            WITH scores AS (
                SELECT
                    model,
                    variant,
                    AVG({_metric}) AS metric_score
                FROM read_csv('{_config["path"]}')
                WHERE {_config["where"]}
                GROUP BY model, variant
            )

            SELECT
                model,
                variant,
                RANK() OVER (
                    ORDER BY metric_score DESC
                ) AS dataset_rank
            FROM scores
            """
        )

    # create the complete tau and shared-pair matrices
    _tau_matrix = pd.DataFrame(
        index=_order,
        columns=_order,
        dtype=float,
    )

    _count_matrix = pd.DataFrame(
        index=_order,
        columns=_order,
        dtype=float,
    )

    # calculate every unique dataset comparison
    for _index, _dataset_a in enumerate(_order):
        _tau_matrix.loc[
            _dataset_a,
            _dataset_a,
        ] = 1.0

        _count_matrix.loc[
            _dataset_a,
            _dataset_a,
        ] = len(_rankings[_dataset_a])

        for _dataset_b in _order[_index + 1 :]:
            # keep pairs found in both datasets
            _shared = pd.merge(
                _rankings[_dataset_a],
                _rankings[_dataset_b],
                on=["model", "variant"],
                how="inner",
                suffixes=("_a", "_b"),
            )

            if len(_shared) >= 2:
                if _tau_method == "Weighted Kendall's tau":
                    # negate ranks so top-ranked pairs receive more weight
                    _tau = weightedtau(
                        -_shared["dataset_rank_a"],
                        -_shared["dataset_rank_b"],
                    ).statistic
                else:
                    _tau = kendalltau(
                        _shared["dataset_rank_a"],
                        _shared["dataset_rank_b"],
                        variant="b",
                        nan_policy="omit",
                    ).statistic
            else:
                _tau = float("nan")

            _count = len(_shared)

            # fill both sides because the matrix is symmetric
            _tau_matrix.loc[
                _dataset_a,
                _dataset_b,
            ] = _tau

            _tau_matrix.loc[
                _dataset_b,
                _dataset_a,
            ] = _tau

            _count_matrix.loc[
                _dataset_a,
                _dataset_b,
            ] = _count

            _count_matrix.loc[
                _dataset_b,
                _dataset_a,
            ] = _count

    # find the selected dataset's category
    _selected_category = configs[_selected_dataset]["category"]

    _average_rows = []

    # choose comparisons for the selected dataset's average
    for _other_dataset in _order:
        if _other_dataset == _selected_dataset:
            continue

        _other_category = configs[_other_dataset]["category"]

        if _scope == "Within the same category" and _other_category != _selected_category:
            continue

        if _scope == "Outside the category" and _other_category == _selected_category:
            continue

        _average_rows.append(
            {
                "selected_dataset": _selected_dataset,
                "comparison_dataset": _other_dataset,
                "selected_category": _selected_category,
                "comparison_category": _other_category,
                "metric": _metric,
                "method": _tau_method,
                "kendall_tau": _tau_matrix.loc[
                    _selected_dataset,
                    _other_dataset,
                ],
                "n_items": _count_matrix.loc[
                    _selected_dataset,
                    _other_dataset,
                ],
            }
        )

    # create the comparisons included in the average
    _average_results = pd.DataFrame(
        _average_rows,
        columns=[
            "selected_dataset",
            "comparison_dataset",
            "selected_category",
            "comparison_category",
            "metric",
            "method",
            "kendall_tau",
            "n_items",
        ],
    ).reset_index(drop=True)

    # calculate the selected dataset's average
    if _average_results.empty:
        _average_tau = float("nan")
        _average_items = float("nan")
    else:
        _average_tau = _average_results["kendall_tau"].mean()

        _average_items = _average_results["n_items"].mean()

    _average_summary = pd.DataFrame(
        [
            {
                "dataset": _selected_dataset,
                "category": _selected_category,
                "metric": _metric,
                "method": _tau_method,
                "scope": _scope,
                "average_kendall_tau": _average_tau,
                "number_of_comparisons": len(_average_results),
                "average_n_items": _average_items,
            }
        ]
    ).round(3)

    _average_results = _average_results.round(
        {
            "kendall_tau": 3,
            "n_items": 0,
        }
    )

    # convert the tau matrix to long-form heat-map data
    _tau_matrix.index.name = "dataset_a"
    _tau_matrix.columns.name = None

    _count_matrix.index.name = "dataset_a"
    _count_matrix.columns.name = None

    _tau_long = _tau_matrix.reset_index().melt(
        id_vars="dataset_a",
        var_name="dataset_b",
        value_name="kendall_tau",
    )

    _count_long = _count_matrix.reset_index().melt(
        id_vars="dataset_a",
        var_name="dataset_b",
        value_name="n_items",
    )

    _heatmap_data = pd.merge(
        _tau_long,
        _count_long,
        on=["dataset_a", "dataset_b"],
        how="left",
    )

    _heatmap_data["display_tau"] = _heatmap_data["kendall_tau"].apply(
        lambda _value: "-" if pd.isna(_value) else f"{_value:.3f}"
    )

    # create shared heat-map axes
    _heatmap_base = alt.Chart(_heatmap_data).encode(
        x=alt.X(
            "dataset_b:N",
            title="Comparison dataset",
            sort=_order,
            axis=alt.Axis(
                labelAngle=-45,
                labelLimit=160,
            ),
        ),
        y=alt.Y(
            "dataset_a:N",
            title="Dataset",
            sort=_order,
            axis=alt.Axis(
                labelLimit=160,
            ),
        ),
    )

    # draw a background for every matrix cell
    _heatmap_background = _heatmap_base.mark_rect(
        color="#e5e7eb",
        stroke="#ffffff",
        strokeWidth=1,
    ).encode(
        tooltip=[
            alt.Tooltip(
                "dataset_a:N",
                title="Dataset",
            ),
            alt.Tooltip(
                "dataset_b:N",
                title="Compared with",
            ),
        ]
    )

    # color cells containing valid tau values
    _heatmap_cells = (
        _heatmap_base.transform_filter("isValid(datum.kendall_tau)")
        .mark_rect(
            stroke="#ffffff",
            strokeWidth=1,
        )
        .encode(
            color=alt.Color(
                "kendall_tau:Q",
                title="Kendall's tau",
                scale=alt.Scale(
                    domain=[
                        -1,
                        -0.001,
                        0,
                        1,
                    ],
                    range=[
                        "#991b1b",
                        "#fca5a5",
                        "#edf8ee",
                        "#166534",
                    ],
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    "dataset_a:N",
                    title="Dataset",
                ),
                alt.Tooltip(
                    "dataset_b:N",
                    title="Compared with",
                ),
                alt.Tooltip(
                    "kendall_tau:Q",
                    title="Kendall's tau",
                    format=".3f",
                ),
                alt.Tooltip(
                    "n_items:Q",
                    title="Shared pairs",
                    format=".0f",
                ),
            ],
        )
    )

    # place the rounded tau inside each cell
    _heatmap_labels = _heatmap_base.mark_text(
        fontSize=11,
        fontWeight="bold",
    ).encode(
        text=alt.Text(
            "display_tau:N",
        ),
        color=alt.condition(
            ("datum.kendall_tau <= -0.55 || datum.kendall_tau >= 0.65"),
            alt.value("#ffffff"),
            alt.value("#1f2937"),
        ),
    )

    _heatmap = (_heatmap_background + _heatmap_cells + _heatmap_labels).properties(
        width=max(300, len(_order) * 50),
        height=max(100, len(_order) * 30),
        title=(f"Full Dataset {_tau_method} Matrix by {_metric}"),
    )

    _method_note = (
        "Weighted Kendall's tau gives more importance to agreement near the top of each ranking."
        if _tau_method == "Weighted Kendall's tau"
        else "Non-weighted Kendall's tau-b gives every ranking position equal importance."
    )

    mo.vstack(
        [
            mo.md(f"**{_selected_dataset} Average {_tau_method} by {_metric}: {_scope}**"),
            mo.md(_method_note),
            _average_summary,
            mo.md("**Comparisons Included in the Average**"),
            _average_results,
            mo.md(f"**Full {_tau_method} Heat Map**"),
            _heatmap,
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Energy Consumption
    """)
    return


@app.cell(hide_code=True)
def _(configs, mo):
    energy_consumption = mo.ui.dropdown(
        options=list(configs.keys()),
        value="ML100K",
        label="Dataset:",
    )

    power_type = mo.ui.radio(
        options=[
            "Infer power",
            "Train power",
        ],
        value="Infer power",
        label="Sort by:",
    )

    mo.vstack([energy_consumption, power_type])
    return energy_consumption, power_type


@app.cell(hide_code=True)
def _(
    config,
    configs,
    dataset,
    energy_consumption,
    mo,
    power_type,
    sort_metric,
):
    _dataset = energy_consumption.value
    _power_type = power_type.value

    _config = configs[dataset]
    _file_path = config["path"]
    _part_value = config["where"]

    if _power_type == "Infer power":
        _power_type = "infer_power"
    else:
        _power_type = "train_power"

    datasets_by_power = mo.sql(
        f"""
        WITH power AS (
        SELECT
            model,
            variant,
            infer_power,
            train_power,
            RANK() OVER (ORDER BY {_power_type} DESC) AS rank
        FROM read_csv('{_file_path}')
        WHERE {_part_value}
        GROUP BY model, variant, infer_power, train_power
        )

        SELECT
            model,
            variant,
            infer_power,
            train_power,
        FROM power
        ORDER BY rank
        """
    )

    if _power_type == "infer_power":
        _power_type = "Infer power"
    else:
        _power_type = "Train power"

    mo.vstack([mo.md(f"**{dataset} Sorted by {sort_metric}**"), datasets_by_power])
    return


if __name__ == "__main__":
    app.run()
