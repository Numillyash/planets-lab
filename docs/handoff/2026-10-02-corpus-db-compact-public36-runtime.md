# Corpus DB compact public36 runtime — 2026-10-02

Canonical compact public36 runtime is green.

Runtime source HEAD:

```text
3739274b797ed6b2e346436e837c4c27849632de
```

Published immutable generation:

```text
corpus-v2compact-public36-20261002T083138Z-11cd75fa918d
sha256 e1c0adc0a699d9d776f1fddb7dfc37c5a6714dfd9262f911a5939fda41cc7004
```

Population:

```text
archives             36
source ZIP bytes     9456773573
turn members         126418
entity rows          314311240
decoded JSON bytes   133808928311
```

Correctness:

```text
parity checked       126418
parity failed        0
shared readers       PASS
CURRENT switched     no
```

Physical result:

```text
compact DB bytes     13189001216
compact DB GiB       ~12.283
typed1 DB bytes      38931017728
reduction typed1     66.12%
reduction decoded    90.14%
DB / source ZIP      1.395x
```

Build:

```text
import               21398.35 s (~5h56m38s)
import peak RSS      13938348032
parity               12541.87 s (~3h29m02s)
parity process RSS   14095867904
```

Query checks on game 233558 inside public36:

```text
T-1/T                0.07015 s / 142249984 RSS
VCR/site             0.02525 s / 117559296 RSS
```

Physical invariants:

```text
entity_rows          absent
decoded_payload_zlib absent
secondary indexes    0
```

Residual:

```text
inline JSON bytes    765900754
missing bytes        1566825204
missing rows         62285221
```

Missing bytes by section:

```text
planets              1023708422
scores                269002122
minefields            160337422
players                97257374
torpedos               16519864
```

Interpretation:

- compact1 is already suitable as the active read backend after a deliberate
  CURRENT switch;
- the next storage optimization should target union-schema presence metadata,
  not native typed data;
- JSON missing-path arrays should be replaced by a compact exact presence mask
  or schema-variant representation;
- no temporal/cross-perspective dedup is needed for that next step;
- retain typed1 until compact activation is deliberately completed and verified.
