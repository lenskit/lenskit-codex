import { dirname, fromFileUrl, relative } from "std/path/mod.ts";

export type Pipeline = {
  params?: string[];
  stages: Record<string, Stage>;
};

export type OutRec = Record<string, { cache: boolean }>;

export type Stage = {
  cmd: string;
  wdir?: string;
  deps?: string[];
  outs?: (string | OutRec)[];
  params?: (string | Record<string, string[]>)[];
  metrics?: (string | OutRec)[];
};

export function action_cmd(origin: string, ...args: string[]): string {
  const script = import.meta.resolve("../action.py");

  if (origin.startsWith("file://")) {
    origin = fromFileUrl(new URL(origin));
  }
  if (origin.endsWith(".ts")) {
    origin = dirname(origin);
  }

  const sloc = relative(origin, fromFileUrl(script));

  let cmd = `python ${sloc}`;
  for (const arg of args) {
    cmd += " " + arg;
  }

  return cmd;
}
