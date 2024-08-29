import { scanStages } from "./pipe-scan.ts";
import { runStages } from "./pipe-runs.ts";
import { exportStages } from "./pipe-export.ts";

export const pipeline = {
  stages: {
    ...scanStages,
    ...runStages,
    ...exportStages,
  },
};
