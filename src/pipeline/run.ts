import { action_cmd, Stage } from "../dvc.ts";
import { resolveProjectPath } from "./paths.ts";

export type Run = {
  name: string;
  split: string;
  variant: string;
  model: string;
  args: string[];
  deps?: string[];
};

export function runPath(run: Run): string {
  return `runs/${run.split}-default/${run.model}`;
}

export function runStages(origin: string, runs: Run[]): Record<string, Stage> {
  let stages: Record<string, Stage> = {};
  for (let run of runs) {
    stages[`run-${run.split}-default-${run.model}`] = {
      cmd: action_cmd(
        "generate",
        ...run.args,
        `--split=splits/${run.split}.toml`,
        `-o runs/${run.split}-default/${run.model}`,
        run.model,
      ),
      outs: [runPath(run)],
      deps: [
        resolveProjectPath(origin, `models/${run.model}.toml`),
        ...(run.deps ?? []),
      ],
    };
  }
  return stages;
}
