import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd

    return mo, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Movielens Datasets**
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    dataset_selector = mo.ui.dropdown(
        options=[
            "100K MovieLens",
            "1M MovieLens",
            "10M MovieLens",
            "20M MovieLens",
            "25M MovieLens",
            "32M MovieLens",
        ],
        value="100K MovieLens",
        label="Dataset:",
    )

    sort_selector = mo.ui.radio(
        options=["RBP", "NDCG"],
        value="RBP",
        label="Rank by:",
    )

    mo.vstack([dataset_selector, sort_selector])
    return dataset_selector, sort_selector


@app.cell(hide_code=True)
def _(dataset_selector, mo, sort_selector):
    dataset_files = {
        "100K MovieLens": ("movielens/ML100K/run-summary.csv", "0"),
        "1M MovieLens": ("movielens/ML1M/run-summary.csv", "0"),
        "10M MovieLens": ("movielens/ML10M/run-summary.csv", "'valid'"),
        "20M MovieLens": ("movielens/ML20M/run-summary.csv", "'valid'"),
        "25M MovieLens": ("movielens/ML25M/run-summary.csv", "'valid'"),
        "32M MovieLens": ("movielens/ML32M/run-summary.csv", "'valid'"),
    }

    dataset = dataset_selector.value
    sort_metric = sort_selector.value

    file_path, part_value = dataset_files[dataset]

    sorted_results = mo.sql(
        f"""
        SELECT
            model,
            variant,
            RBP,
            NDCG,
            RANK() OVER (ORDER BY {sort_metric} DESC) AS rank
        FROM read_csv('{file_path}')
        WHERE part = {part_value}
        GROUP BY model, variant, RBP, NDCG
        ORDER BY rank
        """
    )

    mo.vstack(
        [
            mo.md(f"**{dataset} Sorted by {sort_metric}**"),
            sorted_results,
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Kendall's Tau-b for MovieLens**
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    comparison_selector = mo.ui.dropdown(
        options=[
            "100K to 1M",
            "1M to 10M",
            "10M to 20M",
            "20M to 25M",
            "25M to 32M",
            "100K to 10M",
            "100K to 20M",
            "100K to 25M",
            "100K to 32M",
        ],
        value="100K to 1M",
        label="Comparison pair:",
    )

    comparison_selector
    return (comparison_selector,)


@app.cell(hide_code=True)
def _(comparison_selector, mo):
    def _():
        from scipy.stats import kendalltau

        dataset_info = {
            "100K": ("movielens/ML100K/run-summary.csv", "0"),
            "1M": ("movielens/ML1M/run-summary.csv", "0"),
            "10M": ("movielens/ML10M/run-summary.csv", "'valid'"),
            "20M": ("movielens/ML20M/run-summary.csv", "'valid'"),
            "25M": ("movielens/ML25M/run-summary.csv", "'valid'"),
            "32M": ("movielens/ML32M/run-summary.csv", "'valid'"),
        }

        comparison_pairs = {
            "100K to 1M": ("100K", "1M"),
            "1M to 10M": ("1M", "10M"),
            "10M to 20M": ("10M", "20M"),
            "20M to 25M": ("20M", "25M"),
            "25M to 32M": ("25M", "32M"),
            "100K to 10M": ("100K", "10M"),
            "100K to 20M": ("100K", "20M"),
            "100K to 25M": ("100K", "25M"),
            "100K to 32M": ("100K", "32M"),
        }

        size_a, size_b = comparison_pairs[comparison_selector.value]

        file_a, part_a = dataset_info[size_a]
        file_b, part_b = dataset_info[size_b]

        rankings = mo.sql(
            f"""
            WITH a_rankings AS (
                SELECT
                    model,
                    variant,
                    RBP,
                    RANK() OVER (ORDER BY RBP DESC) AS rank_a
                FROM read_csv('{file_a}')
                WHERE part = {part_a}
            ),

            b_rankings AS (
                SELECT
                    model,
                    variant,
                    RBP,
                    RANK() OVER (ORDER BY RBP DESC) AS rank_b
                FROM read_csv('{file_b}')
                WHERE part = {part_b}
            )

            SELECT
                a.model,
                a.variant,
                a.RBP AS RBP_{size_a},
                b.RBP AS RBP_{size_b},
                a.rank_a,
                b.rank_b
            FROM a_rankings AS a
            INNER JOIN b_rankings AS b
                ON a.model = b.model
                AND a.variant = b.variant
            ORDER BY a.rank_a
            """
        )

        tau, p_value = kendalltau(
            rankings["rank_a"],
            rankings["rank_b"],
            variant="b",
            nan_policy="omit",
        )

        if tau <= -0.97:
            interpretation = "completely disagree across the datasets."
        elif tau <= -0.9:
            interpretation = "nearly completely disagree across the datasets."

        elif tau <= -0.75:
            interpretation = "strongly disagree across the datasets."
        elif tau <= -0.5:
            interpretation = "disagree across the datasets."
        elif tau <= -0.25:
            interpretation = "slightly disagree across the datasets."
        elif tau < 0.25:
            interpretation = "have little to no correlation across the datasets."
        elif tau <= 0.5:
            interpretation = "slightly agree across the datasets."
        elif tau <= 0.75:
            interpretation = "agree across the datasets."
        elif tau < 0.9:
            interpretation = "strongly agree across the datasets."
        elif tau < 0.97:
            interpretation = "nearly completely agree across the datasets."
        else:
            interpretation = "completely agree across the datasets."
        return mo.md(
            f"""
            **Kendall's Tau-b: {size_a} to {size_b}**

            **Tau-b:** `{tau:.4f}`
            **Number of shared model-variant pairs:** `{len(rankings)}`

            The rankings of the model-variant pairs {interpretation}
            """
        )

    _()
    return


@app.cell(hide_code=True)
def _(mo):
    metric_selector = mo.ui.radio(
        options=["RBP", "NDCG"],
        value="RBP",
        label="Sort rankings by:",
    )

    metric_selector
    return (metric_selector,)


@app.cell(hide_code=True)
def _(metric_selector, mo):
    def _():
        import altair as alt
        import pandas as pd
        from scipy.stats import kendalltau

        metric = metric_selector.value

        dataset_info = {
            "100K": ("movielens/ML100K/run-summary.csv", "0"),
            "1M": ("movielens/ML1M/run-summary.csv", "0"),
            "10M": ("movielens/ML10M/run-summary.csv", "'valid'"),
            "20M": ("movielens/ML20M/run-summary.csv", "'valid'"),
            "25M": ("movielens/ML25M/run-summary.csv", "'valid'"),
            "32M": ("movielens/ML32M/run-summary.csv", "'valid'"),
        }

        comparison_groups = {
            "Adjacent comparisons": [
                ("100K", "1M"),
                ("1M", "10M"),
                ("10M", "20M"),
                ("20M", "25M"),
                ("25M", "32M"),
            ],
            "100K baseline comparisons": [
                ("100K", "1M"),
                ("100K", "10M"),
                ("100K", "20M"),
                ("100K", "25M"),
                ("100K", "32M"),
            ],
        }

        rows = []

        for group_name, comparisons in comparison_groups.items():
            for size_a, size_b in comparisons:
                file_a, part_a = dataset_info[size_a]
                file_b, part_b = dataset_info[size_b]

                rankings = mo.sql(
                    f"""
                    WITH a_rankings AS (
                        SELECT
                            model,
                            variant,
                            {metric},
                            RANK() OVER (ORDER BY {metric} DESC) AS rank_a
                        FROM read_csv('{file_a}')
                        WHERE part = {part_a}
                    ),

                    b_rankings AS (
                        SELECT
                            model,
                            variant,
                            {metric},
                            RANK() OVER (ORDER BY {metric} DESC) AS rank_b
                        FROM read_csv('{file_b}')
                        WHERE part = {part_b}
                    )

                    SELECT
                        a.model,
                        a.variant,
                        a.{metric} AS metric_a,
                        b.{metric} AS metric_b,
                        a.rank_a,
                        b.rank_b
                    FROM a_rankings AS a
                    INNER JOIN b_rankings AS b
                        ON a.model = b.model
                        AND a.variant = b.variant
                    ORDER BY a.rank_a
                    """
                )

                tau, p_value = kendalltau(
                    rankings["rank_a"],
                    rankings["rank_b"],
                    variant="b",
                    nan_policy="omit",
                )

                rows.append(
                    {
                        "group": group_name,
                        "comparison": f"{size_a} to {size_b}",
                        "kendall_tau": tau,
                        "p_value": p_value,
                        "n_items": len(rankings),
                    }
                )

        kendall_results = pd.DataFrame(rows)

        adjacent_chart = (
            alt.Chart(kendall_results[kendall_results["group"] == "Adjacent comparisons"])
            .mark_line(point=True)
            .encode(
                x=alt.X("comparison:N", sort=None, title="Comparison"),
                y=alt.Y(
                    "kendall_tau:Q",
                    title=f"Kendall's tau-b sorted by {metric}",
                    scale=alt.Scale(domain=[-1, 1]),
                ),
                tooltip=["comparison", "kendall_tau", "p_value", "n_items"],
            )
            .properties(width=700, height=300)
        )

        baseline_chart = (
            alt.Chart(kendall_results[kendall_results["group"] == "100K baseline comparisons"])
            .mark_line(point=True)
            .encode(
                x=alt.X("comparison:N", sort=None, title="Comparison"),
                y=alt.Y(
                    "kendall_tau:Q",
                    title=f"Kendall's tau-b sorted by {metric}",
                    scale=alt.Scale(domain=[-1, 1]),
                ),
                tooltip=["comparison", "kendall_tau", "p_value", "n_items"],
            )
            .properties(width=700, height=300)
        )
        return mo.vstack(
            [
                mo.md(f"**Adjacent Comparisons Sorted by {metric}**"),
                adjacent_chart,
                mo.md(f"**100K Baseline Comparisons Sorted by {metric}**"),
                baseline_chart,
            ]
        )

    _()
    return


@app.cell(hide_code=True)
def _(mo):
    top_metric_selector = mo.ui.radio(
        options=["RBP", "NDCG"],
        value="RBP",
        label="Metric for top model-variant pair",
    )

    top_metric_selector
    return (top_metric_selector,)


@app.cell(hide_code=True)
def _(mo, top_metric_selector):
    metric = top_metric_selector.value

    top_tracking = mo.sql(
        f"""
        WITH all_rankings AS (
            SELECT
                '100K' AS dataset,
                model,
                variant,
                RBP,
                NDCG,
                RANK() OVER (ORDER BY {metric} DESC) AS rank
            FROM read_csv('movielens/ML100K/run-summary.csv')
            WHERE part = 0

            UNION ALL

            SELECT
                '1M' AS dataset,
                model,
                variant,
                RBP,
                NDCG,
                RANK() OVER (ORDER BY {metric} DESC) AS rank
            FROM read_csv('movielens/ML1M/run-summary.csv')
            WHERE part = 0

            UNION ALL

            SELECT
                '10M' AS dataset,
                model,
                variant,
                RBP,
                NDCG,
                RANK() OVER (ORDER BY {metric} DESC) AS rank
            FROM read_csv('movielens/ML10M/run-summary.csv')
            WHERE part = 'valid'

            UNION ALL

            SELECT
                '20M' AS dataset,
                model,
                variant,
                RBP,
                NDCG,
                RANK() OVER (ORDER BY {metric} DESC) AS rank
            FROM read_csv('movielens/ML20M/run-summary.csv')
            WHERE part = 'valid'

            UNION ALL

            SELECT
                '25M' AS dataset,
                model,
                variant,
                RBP,
                NDCG,
                RANK() OVER (ORDER BY {metric} DESC) AS rank
            FROM read_csv('movielens/ML25M/run-summary.csv')
            WHERE part = 'valid'

            UNION ALL

            SELECT
                '32M' AS dataset,
                model,
                variant,
                RBP,
                NDCG,
                RANK() OVER (ORDER BY {metric} DESC) AS rank
            FROM read_csv('movielens/ML32M/run-summary.csv')
            WHERE part = 'valid'
        )

        SELECT
            dataset,
            model,
            variant,
            RBP,
            NDCG,
            rank
        FROM all_rankings
        WHERE rank = 1
        ORDER BY
            CASE dataset
                WHEN '100K' THEN 1
                WHEN '1M' THEN 2
                WHEN '10M' THEN 3
                WHEN '20M' THEN 4
                WHEN '25M' THEN 5
                WHEN '32M' THEN 6
            END
        """
    )

    mo.vstack(
        [
            mo.md(f"**Best Model-Variant Pair of Each Dataset by {metric}**"),
            top_tracking,
        ]
    )
    return


@app.cell(hide_code=True)
def _(mo):

    category_avg_metric_selector = mo.ui.radio(
        options=["RBP", "NDCG"],
        value="RBP",
        label="Rank category averages by:",
    )

    category_avg_metric_selector

    # don't know if this will be useful
    return (category_avg_metric_selector,)


@app.cell(hide_code=True)
def _(category_avg_metric_selector, mo, pd):
    from itertools import combinations

    import altair as alt
    from scipy.stats import kendalltau

    category_avg_metric = category_avg_metric_selector.value

    category_avg_datasets = {
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
    }

    category_avg_pair_rows = []

    for category_avg_dataset_a, category_avg_dataset_b in combinations(
        category_avg_datasets.keys(), 2
    ):
        category_a = category_avg_datasets[category_avg_dataset_a]["category"]
        category_b = category_avg_datasets[category_avg_dataset_b]["category"]

        # average datasets inside the same category.
        # MovieLens pairs with MovieLens, Amazon pairs with Amazon, etc.
        if category_a != category_b:
            continue

        path_a = category_avg_datasets[category_avg_dataset_a]["path"]
        path_b = category_avg_datasets[category_avg_dataset_b]["path"]
        where_a = category_avg_datasets[category_avg_dataset_a]["where"]
        where_b = category_avg_datasets[category_avg_dataset_b]["where"]

        category_avg_rankings = mo.sql(
            f"""
            WITH a_rankings AS (
                SELECT
                    model,
                    variant,
                    {category_avg_metric},
                    RANK() OVER (ORDER BY {category_avg_metric} DESC) AS rank_a
                FROM read_csv('{path_a}')
                WHERE {where_a}
                GROUP BY model, variant, {category_avg_metric}
            ),

            b_rankings AS (
                SELECT
                    model,
                    variant,
                    {category_avg_metric},
                    RANK() OVER (ORDER BY {category_avg_metric} DESC) AS rank_b
                FROM read_csv('{path_b}')
                WHERE {where_b}
                GROUP BY model, variant, {category_avg_metric}
            )

            SELECT
                a.model,
                a.variant,
                a.rank_a,
                b.rank_b
            FROM a_rankings AS a
            INNER JOIN b_rankings AS b
                ON a.model = b.model
                AND a.variant = b.variant
            """
        )

        category_avg_tau, category_avg_p_value = kendalltau(
            category_avg_rankings["rank_a"],
            category_avg_rankings["rank_b"],
            variant="b",
            nan_policy="omit",
        )

        category_avg_pair_rows.append(
            {
                "category": category_a,
                "dataset_a": category_avg_dataset_a,
                "dataset_b": category_avg_dataset_b,
                "comparison": f"{category_avg_dataset_a} to {category_avg_dataset_b}",
                "kendall_tau": category_avg_tau,
                "p_value": category_avg_p_value,
                "n_items": len(category_avg_rankings),
            }
        )

    category_avg_pairwise_results = pd.DataFrame(category_avg_pair_rows)

    category_avg_results = category_avg_pairwise_results.groupby("category", as_index=False).agg(
        average_kendall_tau=("kendall_tau", "mean"),
        number_of_comparisons=("kendall_tau", "count"),
        average_n_items=("n_items", "mean"),
    )

    category_avg_chart = (
        alt.Chart(category_avg_results)
        .mark_bar()
        .encode(
            x=alt.X("category:N", title="Dataset category"),
            y=alt.Y(
                "average_kendall_tau:Q",
                title=f"Average Kendall's tau-b sorted by {category_avg_metric}",
                scale=alt.Scale(domain=[-1, 1]),
            ),
            color=alt.value("#66deca"),
            tooltip=[
                "category",
                "average_kendall_tau",
                "number_of_comparisons",
                "average_n_items",
            ],
        )
        .properties(width=500, height=350)
    )

    if category_avg_tau <= -0.97:
        interpretation = "completely disagree across the datasets."
    elif category_avg_tau <= -0.9:
        interpretation = "nearly completely disagree across the datasets."
    elif category_avg_tau <= -0.75:
        interpretation = "strongly disagree across the datasets."
    elif category_avg_tau <= -0.5:
        interpretation = "disagree across the datasets."
    elif category_avg_tau <= -0.25:
        interpretation = "slightly disagree across the datasets."
    elif category_avg_tau < 0.25:
        interpretation = "have little to no correlation across the datasets."
    elif category_avg_tau <= 0.5:
        interpretation = "slightly agree across the datasets."
    elif category_avg_tau <= 0.75:
        interpretation = "agree across the datasets."
    elif category_avg_tau < 0.9:
        interpretation = "strongly agree across the datasets."
    elif category_avg_tau < 0.97:
        interpretation = "nearly completely agree across the datasets."
    else:
        interpretation = "completely agree across the datasets."

    mo.vstack(
        [
            mo.md(
                f"**Pairwise Kendall's Tau-b by Dataset Category Sorted by {category_avg_metric}**"
            ),
            category_avg_pairwise_results,
            mo.md("**Average Kendall's Tau-b by Dataset Category**"),
            category_avg_results,
            category_avg_chart,
            mo.md(f"The rankings of the model-variant pairs {interpretation}"),
        ]
    )

    # bar chart looks incomplete until other categories of datasets are added
    return (alt,)


@app.cell
def _():
    import altair as alt

    return (alt,)


@app.cell
def _():
    import altair as alt

    return (alt,)


@app.cell(hide_code=True)
def _(mo):
    top_pair_metric_selector = mo.ui.radio(
        options=["RBP", "NDCG"],
        value="RBP",
        label="Rank top model-variant pairs by:",
    )

    top_pair_metric_selector
    return (top_pair_metric_selector,)


@app.cell(hide_code=True)
def _(mo, pd, top_pair_metric_selector):
    top_pair_metric = top_pair_metric_selector.value

    top_pair_dataset_configs = {
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
    }

    top_pair_rows = []

    for top_pair_dataset_name, top_pair_config in top_pair_dataset_configs.items():
        top_pair_category = top_pair_config["category"]
        top_pair_path = top_pair_config["path"]
        top_pair_where = top_pair_config["where"]

        top_pair_rankings = mo.sql(
            f"""
            SELECT
                model,
                variant,
                RBP,
                NDCG,
                ROW_NUMBER() OVER (ORDER BY {top_pair_metric} DESC) AS top_rank
            FROM read_csv('{top_pair_path}')
            WHERE {top_pair_where}
            GROUP BY model, variant, RBP, NDCG
            ORDER BY top_rank
            """
        )

        top_three = top_pair_rankings[top_pair_rankings["top_rank"] <= 3]

        for _, row in top_three.iterrows():
            if row["top_rank"] == 1:
                points = 1
            elif row["top_rank"] == 2:
                points = 2 / 3
            elif row["top_rank"] == 3:
                points = 1 / 3
            else:
                points = 0

            top_pair_rows.append(
                {
                    "dataset": top_pair_dataset_name,
                    "category": top_pair_category,
                    "model": row["model"],
                    "variant": row["variant"],
                    "metric": top_pair_metric,
                    "score": row[top_pair_metric],
                    "top_rank": row["top_rank"],
                    "points": points,
                }
            )

    top_pair_points = pd.DataFrame(top_pair_rows)

    top_pair_total_points = (
        top_pair_points.groupby(["model", "variant"], as_index=False)
        .agg(
            total_points=("points", "sum"),
            times_in_top_3=("points", "count"),
        )
        .sort_values("total_points", ascending=False)
    )

    top_pair_category_points = (
        top_pair_points.groupby(["category", "model", "variant"], as_index=False)
        .agg(
            category_points=("points", "sum"),
            times_in_top_3=("points", "count"),
        )
        .sort_values(["category", "category_points"], ascending=[True, False])
    )

    top_pair_total_points
    return top_pair_category_points, top_pair_total_points


@app.cell(hide_code=True)
def _(mo, top_pair_category_points):
    top_pair_category_options = ["ALL"] + sorted(
        top_pair_category_points["category"].unique().tolist()
    )

    top_pair_category_selector = mo.ui.dropdown(
        options=top_pair_category_options,
        value="ALL",
        label="Choose dataset category:",
    )

    top_pair_category_selector
    return (top_pair_category_selector,)


@app.cell(hide_code=True)
def _(
    alt,
    mo,
    top_pair_category_points,
    top_pair_category_selector,
    top_pair_total_points,
):
    selected_top_pair_category = top_pair_category_selector.value

    if selected_top_pair_category == "ALL":
        selected_top_pair_points = top_pair_total_points.copy()
        selected_points_column = "total_points"
        selected_title = "All Dataset Categories"
    else:
        selected_top_pair_points = top_pair_category_points[
            top_pair_category_points["category"] == selected_top_pair_category
        ].copy()
        selected_points_column = "category_points"
        selected_title = selected_top_pair_category

    selected_top_pair_chart = (
        alt.Chart(selected_top_pair_points.head(15))
        .mark_bar()
        .encode(
            x=alt.X(f"{selected_points_column}:Q", title="Points"),
            y=alt.Y(
                "model_variant:N",
                sort="-x",
                title="Model-variant pair",
            ),
            color=alt.value("#66deca"),
            tooltip=[
                "model",
                "variant",
                selected_points_column,
                "times_in_top_3",
            ],
        )
        .transform_calculate(model_variant="datum.model + ' / ' + datum.variant")
        .properties(width=700, height=400)
    )

    mo.vstack(
        [
            mo.md(f"**Top Model-Variant Pairs: {selected_title}**"),
            selected_top_pair_points,
            selected_top_pair_chart,
        ]
    )
    return


if __name__ == "__main__":
    app.run()
