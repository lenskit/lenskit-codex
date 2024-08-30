export type ModelInfo = {
  predictor?: boolean;
  sweepable: boolean;
};

export const MODELS: Record<string, ModelInfo> = {
  "Bias": { sweepable: true, predictor: true },
  "Popular": { sweepable: false },
  "BiasedMF-ALS": { sweepable: true, predictor: true },
  "ImplicitMF-ALS": { sweepable: true },
  "IKNN-Explicit": { sweepable: true, predictor: true },
  "IKNN-Implicit": { sweepable: true },
  "UKNN-Explicit": { sweepable: true, predictor: true },
  "UKNN-Implicit": { sweepable: true },
  "Implicit-BPR": { sweepable: true },
  "HPF": { sweepable: true },
};
