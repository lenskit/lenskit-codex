export type Pipeline = {
  params?: string[];
  stages: Record<string, Stage>;
};

export type OutRec = Record<string, { cache: boolean }>;

export type SingleStage = {
  cmd: string;
  wdir?: string;
  deps?: string[];
  outs?: (string | OutRec)[];
  params?: (string | Record<string, string[]>)[];
  metrics?: (string | OutRec)[];
};
export type MultiStage = {
  foreach: string[] | Record<string, string>[];
  do: SingleStage;
};
export type Stage = SingleStage | MultiStage;

export function isSingleStage(obj: object): obj is SingleStage {
  return Object.hasOwn(obj, "cmd");
}
export function isMultiStage(obj: object): obj is MultiStage {
  return Object.hasOwn(obj, "foreach");
}
export function isStage(obj: object): obj is Stage {
  return Object.hasOwn(obj, "cmd") || Object.hasOwn(obj, "foreach");
}

export function action_cmd(...args: string[]): string {
  let cmd = "lenskit-codex";
  for (const arg of args) {
    cmd += " " + arg;
  }

  return cmd;
}

export function lk_cmd(...args: string[]): string {
  let cmd = "lenskit";
  for (const arg of args) {
    cmd += " " + arg;
  }

  return cmd;
}

export function generateStages<T>(
  inputs: Iterable<T>,
  func: (x: T) => Record<string, Stage>,
): Record<string, Stage> {
  let obj: Record<string, Stage> = {};
  for (let x of inputs) {
    Object.assign(obj, func(x));
  }
  return obj;
}
