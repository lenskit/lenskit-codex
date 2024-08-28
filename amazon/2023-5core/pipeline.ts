import { scanStages } from "./pipe-scan.ts";
import { runStages } from "./pipe-runs.ts";

export const pipeline = {
  stages: {
    ...scanStages,
    ...runStages,
  },
};
