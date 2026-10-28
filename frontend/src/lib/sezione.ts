export interface SezioneVisibile {
  id: string;
}

/**
 * Keeps a deep-linked section intact until the user's view has loaded.
 * Afterwards a hidden or unknown section falls back to the first visible one.
 */
export function sezioneAttiva(
  sezioneRichiesta: string,
  sezioniVisibili: SezioneVisibile[],
  vistaPronta: boolean,
): string {
  if (!vistaPronta || sezioniVisibili.length === 0) return sezioneRichiesta;

  return sezioniVisibili.some(({ id }) => id === sezioneRichiesta)
    ? sezioneRichiesta
    : sezioniVisibili[0].id;
}
