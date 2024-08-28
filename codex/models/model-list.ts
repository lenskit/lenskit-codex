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
  "Implicit-BPR": { sweepable: false },
  "HPF": { sweepable: false },
};
