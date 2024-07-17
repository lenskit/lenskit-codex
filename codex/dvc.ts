export type Pipeline = {
  stages: Record<string, Stage>;
};

export type OutRec = Record<string, { cache: boolean }>;

export type Stage = {
  cmd: string;
  wdir?: string;
  deps?: string[];
  outs?: (string | OutRec)[];
  metrics?: (string | OutRec)[];
};
