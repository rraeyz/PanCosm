"""Harmonic, combination and daily-alias notes for a list of prewhitened frequencies.

A frequency is flagged when it lies within the resolution 1.5/T (Loumos & Deeming 1978, Ap&SS 56, 285; T = the time
span) of n*f_i (n = 2..5), of f_i +- f_j, or of f_i +- k*1.0027 c/d (k = 1, 2; the sidereal day), with i, j
earlier (stronger) in the list. Always listed, also for space data: the user judges, so the notes say "possible".
"""

SIDEREAL_DAY = 1.0027379  # c/d


def combination_notes(freqs, span):
    """Per frequency a list of JSON-safe dicts: {"kind": "harmonic", "n", "i"}, {"kind": "combination", "i", "j",
    "sign"} or {"kind": "alias", "i", "k"}; i, j are 1-based positions in `freqs`."""
    res = 1.5 / span
    out = []
    for m, f in enumerate(freqs):
        notes = []
        for i in range(m):
            fi = freqs[i]
            notes += [{"kind": "harmonic", "n": n, "i": i + 1} for n in range(2, 6) if abs(f - n * fi) < res]
            for j in range(i):
                for sign in (1, -1):
                    if abs(f - (fi + sign * freqs[j])) < res:
                        notes.append({"kind": "combination", "i": i + 1, "j": j + 1, "sign": sign})
            for k in (-2, -1, 1, 2):
                if abs(f - (fi + k * SIDEREAL_DAY)) < res:
                    notes.append({"kind": "alias", "i": i + 1, "k": k})
        out.append(notes)
    return out
