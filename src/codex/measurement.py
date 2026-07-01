from lenskit.metrics import (
    DCG,
    MAE,
    NDCG,
    RBP,
    RMSE,
    Hit,
    ListLength,
    MeasurementCollector,
    Recall,
    RecipRank,
)


def topn_collector() -> MeasurementCollector:
    mc = MeasurementCollector()

    mc.add_metric(ListLength)
    # mc.add_metric(TestItemCount)
    # mc.add_metric(ListGini)
    # mc.add_metric(ExposureGini)
    # mc.add_metric(MeanPopRank)
    mc.add_metric(RBP)
    mc.add_metric(DCG)
    mc.add_metric(NDCG)
    mc.add_metric(RecipRank)
    mc.add_metric(Hit(k=5))
    mc.add_metric(Hit(k=10))
    mc.add_metric(Hit)
    mc.add_metric(Recall(k=10))
    mc.add_metric(Recall)

    return mc


def prediction_collector() -> MeasurementCollector:
    mc = MeasurementCollector()
    mc.add_metric(RMSE)
    mc.add_metric(MAE)

    return mc
