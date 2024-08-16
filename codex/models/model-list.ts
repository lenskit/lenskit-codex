export type ModelInfo = {
  sweepable: boolean;
};

export const MODELS: Record<string, ModelInfo> = {
  "Bias": { sweepable: true },
  "Popular": { sweepable: false },
  "BiasedMF-ALS": { sweepable: true },
  "ImplicitMF-ALS": { sweepable: true },
  "IKNN_Explicit": { sweepable: true },
  "IKNN_Implicit": { sweepable: true },
};
