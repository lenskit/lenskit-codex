import { dirname, fromFileUrl } from "std/path/mod.ts";

export function resolveProjectPath(origin: string, path: string): string {
  if (origin.startsWith("file://")) {
    origin = fromFileUrl(new URL(origin));
  }
  if (origin.endsWith(".ts")) {
    origin = dirname(origin);
  }
  let parts = origin.split("/");
  for (let _p of parts) {
    path = "../" + path;
  }
  return path;
}
