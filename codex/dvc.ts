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
