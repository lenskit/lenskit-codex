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
    **100K Sorted by RBP**
    """)
    return


@app.cell
def _(mo):
    RBP100K = mo.sql(
        f"""
        SELECT  
            model,
            variant,
            RBP, 
            NDCG, 
        	RANK() OVER (ORDER BY RBP DESC) as rank
        FROM read_csv("movielens/ML100K/run-summary.csv")
        WHERE part=0
        GROUP BY model, variant, RBP, NDCG
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **100K Sorted by NDCG**
    """)
    return


@app.cell
def _(mo):
    NDCG100K = mo.sql(
        f"""
        SELECT  
            model,
            variant,
            RBP, 
            NDCG, 
        	RANK() OVER (ORDER BY NDCG DESC) as rank
        FROM read_csv("movielens/ML100K/run-summary.csv")
        WHERE part=0
        GROUP BY model, variant, RBP, NDCG
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **1M Sorted by RBP**
    """)
    return


@app.cell
def _(mo):
    RBP1M = mo.sql(
        f"""
        SELECT  
            model,
            variant,
            RBP, 
            NDCG, 
        	RANK() OVER (ORDER BY RBP DESC) as rank
        FROM read_csv("movielens/ML1M/run-summary.csv")
        WHERE part=0
        GROUP BY model, variant, RBP, NDCG
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **1M Sorted by NDCG**
    """)
    return


@app.cell
def _(mo):
    NDCG1M = mo.sql(
        f"""
        SELECT  
            model,
            variant,
            RBP, 
            NDCG, 
        	RANK() OVER (ORDER BY NDCG DESC) as rank
        FROM read_csv("movielens/ML1M/run-summary.csv")
        WHERE part=0
        GROUP BY model, variant, RBP, NDCG
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **10M Sorted by RBP**
    """)
    return


@app.cell
def _(mo):
    RBP10M = mo.sql(
        f"""
        SELECT  
            model,
            variant,
            RBP, 
            NDCG, 
        	RANK() OVER (ORDER BY RBP DESC) as rank
        FROM read_csv("movielens/ML10M/run-summary.csv")
        WHERE part='valid'
        GROUP BY model, variant, RBP, NDCG
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **10M Sorted by NDCG**
    """)
    return


@app.cell
def _(mo):
    NDCG10M = mo.sql(
        f"""
        SELECT  
            model,
            variant,
            RBP, 
            NDCG, 
        	RANK() OVER (ORDER BY NDCG DESC) as rank
        FROM read_csv("movielens/ML10M/run-summary.csv")
        WHERE part='valid'
        GROUP BY model, variant, RBP, NDCG
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Kendall's Tau for 100K and 1M**
    """)
    return


@app.cell
def _(mo):
    NDCGhtom = mo.sql(
        f"""
        WITH ht_rankings AS (
            SELECT
                model,
                variant,
                RBP,
                RANK() OVER (ORDER BY RBP DESC) AS ht_rank
            FROM read_csv('movielens/ML100K/run-summary.csv')
            WHERE part = 0
        ),

        om_rankings AS (
            SELECT
                model,
                variant,
                RBP,
                RANK() OVER (ORDER BY RBP DESC) AS om_rank
            FROM read_csv('movielens/ML1M/run-summary.csv')
            WHERE part = 0
        )

        SELECT
            ht.model,
            ht.variant,
            ht.RBP AS ht_RBP,
            om.RBP AS om_RBP,
            ht.ht_rank,
            om.om_rank
        FROM ht_rankings AS ht
        INNER JOIN om_rankings AS om
            ON ht.model = om.model
            AND ht.variant = om.variant
        ORDER BY ht.ht_rank;
        """
    )
    return (NDCGhtom,)


@app.cell
def _(NDCGhtom):
    import numpy as np
    from scipy.stats import kendalltau

    #ht stands for hundred thousand
    #om stands for one million

    rankings = NDCGhtom

    tau, p_value = kendalltau(
        rankings["ht_rank"],
        rankings["om_rank"],
        variant="b",
        nan_policy="omit"
    )

    print(f"Kendall's Tau-b: {tau:.4f}")

    #interpretations in increments of 0.25
    if tau <= -0.75:
        print("The rankings of the model-variant pairs completely disagree across the datasets.")
    elif tau <= -0.5:
        print("The rankings of the model-varaint pairs disagree across the datasets.")
    elif tau <=-0.25:
        print("The rankings of model-variant pairs slightly disagree across the datasets.")
    elif tau <=-0:
        print("The rankings of model-variant pairs ")
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
