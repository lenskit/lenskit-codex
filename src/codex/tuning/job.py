from dataclasses import dataclass, field

import numpy as np
import ray
from lenskit.splitting import TTSplit

from codex.runlog import DataModel

DEFAULT_MAX_EPOCHS = 100


@dataclass
class TuningJobData:
    """
    Data and configuration for a tuning run.
    """

    model_name: str
    list_length: int
    random_seed: np.random.SeedSequence
    epoch_limit: int = DEFAULT_MAX_EPOCHS
    data_info: DataModel = field(default_factory=DataModel)

    factory_ref: ray.ObjectRef | None = None
    data_ref: ray.ObjectRef | None = None

    @property
    def data_name(self):
        return self.data_info.dataset

    @property
    def factory(self):
        if self.factory_ref is None:
            return None
        else:
            return ray.get(self.factory_ref)

    @property
    def data(self) -> TTSplit:
        assert self.data_ref is not None
        return ray.get(self.data_ref)
