export type ModelInfo = {
  sweepable: boolean;
};

export const MODELS: Record<string, ModelInfo> = {
  "Bias": { sweepable: true },
  "Popular": { sweepable: false },
  "BiasedMF-ALS": { sweepable: true },
  "ImplicitMF-ALS": { sweepable: true },
  "IKNN-Explicit": { sweepable: true },
  "IKNN-Implicit": { sweepable: true },
};
