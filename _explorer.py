import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Movielens Datasets**
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    dataset_selector = mo.ui.radio(
        options=["100K MovieLens", "1M MovieLens", "10M MovieLens", "20M MovieLens", "25M MovieLens", "32M MovieLens"],
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

    mo.vstack([
        mo.md(f"**{dataset} Sorted by {sort_metric}**"),
        sorted_results,
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Kendall's Tau for MovieLens**
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    comparison_selector = mo.ui.radio(
        options=[
            "100K to 1M",
            "1M to 10M",
            "10M to 20M",
            "20M to 25M",
            "25M to 32M",
            "100K to 10M",
            "100K to 20M",
            "100K to 25M",
            "100K to 32M"
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
            interpretation = "The rankings of the model-variant pairs completely disagree across the datasets."
        elif tau <= -0.9:
            interpretation = "The rankings of the model-variant pairs nearly completely disagree across the datasets."
        elif tau <= -0.75:
            interpretation = "The rankings of the model-variant pairs strongly disagree across the datasets."
        elif tau <= -0.5:
            interpretation = "The rankings of the model-variant pairs disagree across the datasets."
        elif tau <= -0.25:
            interpretation = "The rankings of the model-variant pairs slightly disagree across the datasets."
        elif tau < 0.25:
            interpretation = "The rankings of the model-variant pairs have little to no correlation across the datasets."
        elif tau <= 0.5:
            interpretation = "The rankings of the model-variant pairs slightly agree across the datasets."
        elif tau <= 0.75:
            interpretation = "The rankings of the model-variant pairs agree across the datasets."
        elif tau < 0.9:
            interpretation = "The rankings of the model-variant pairs strongly agree across the datasets."
        elif tau < 0.97:
            interpretation = "The rankings of the model-variant pairs nearly completely agree across the datasets."
        else:
            interpretation = "The rankings of the model-variant pairs completely agree across the datasets."
        return mo.md(
            f"""
            **Kendall's Tau-b: {size_a} to {size_b}**

            **Tau-b:** `{tau:.4f}`  
            **Number of shared model-variant pairs:** `{len(rankings)}`

            {interpretation}
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
        from scipy.stats import kendalltau
        import pandas as pd
        import altair as alt

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

                rows.append({
                    "group": group_name,
                    "comparison": f"{size_a} to {size_b}",
                    "kendall_tau": tau,
                    "p_value": p_value,
                    "n_items": len(rankings),
                })

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
        return mo.vstack([
            mo.md(f"**Adjacent Comparisons Sorted by {metric}**"),
            adjacent_chart,
            mo.md(f"**100K Baseline Comparisons Sorted by {metric}**"),
            baseline_chart,
        ])


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

    mo.vstack([
        mo.md(f"**Best Model-Variant Pair of Each Dataset by {metric}**"),
        top_tracking,
    ])
    return


if __name__ == "__main__":
    app.run()
