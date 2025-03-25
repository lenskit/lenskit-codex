"""
Codex pipeline tools.
"""

from lenskit.basic import BiasScorer
from lenskit.data import ItemList, QueryInput
from lenskit.pipeline import Component, Pipeline, PipelineBuilder, RecPipelineBuilder


def base_pipeline(
    name: str, scorer: Component | None = None, predicts_ratings: bool = False
) -> Pipeline:
    """
    Build a base top-N pipeline, using a placeholder if no scorer is provided.
    """
    builder = RecPipelineBuilder()
    if scorer is None:
        scorer = DummyScorer()
    builder.scorer(scorer)
    if predicts_ratings:
        builder.predicts_ratings(fallback=BiasScorer())

    return builder.build(name)


def replace_scorer(pipe: Pipeline, scorer: Component) -> Pipeline:
    bld = PipelineBuilder.from_pipeline(pipe)
    bld.replace_component(
        "scorer", scorer, query=pipe.node("query"), items=pipe.node("candidate-selector")
    )
    return bld.build()


class DummyScorer(Component):
    """
    Scorer that does nothing.
    """

    config: None

    def __call__(self, query: QueryInput, items: ItemList) -> ItemList:
        return ItemList()
