// @ts-nocheck
import { describe, expect, it } from "vitest";
import { sezioneAttiva } from "./sezione.ts";

describe("sezioneAttiva", () => {
  it("keeps a deep link while the vista is loading", () => {
    expect(sezioneAttiva("salvati", [], false)).toBe("salvati");
  });

  it("falls back to the first visible section once the vista is ready", () => {
    expect(
      sezioneAttiva(
        "salvati",
        [{ id: "cerca" }, { id: "risultati" }],
        true,
      ),
    ).toBe("cerca");
  });
});
