# Private game 686764 prospective capture adapter — ready

Date: 2026-10-05

Status:

    SNAPSHOT_ADAPTER_READY

## Purpose

The next capture-side discriminator is rare in random public corpora:

    first occurrence
    capture side LEFT
    existing O-order pair not reachable
    capture-created C-forward continuation

The post-prospective candidate predicts:

    C-order prize side = RIGHT

Private game 686764 is preferred for the next prospective test because the
controlled Gemtriot can be used to arrange the required scenario deliberately.

This work does not ingest private data into immutable public100 and does not
publish private raw state to GitHub.

## Authenticated loadturn path

The adapter extends the existing stdlib Planets.nu client with the authenticated
request shape already used by the separate planets-intel client:

    POST game/loadturn
    gameid=<id>
    apikey=<secret>
    forsave=true
    activity=true
    turn=<optional historical turn>

The API key is sent only in the POST body. It is never placed in the URL.

## Local raw-state boundary

Fetch command:

    tools/run-private-turn-snapshot.sh fetch --game-id 686764

The wrapper reads:

    PLANETSNU_API_KEY

from the environment and never prints it.

The sanitized loadturn payload is written only under:

    data/raw/private-turns/

That directory is already covered by the repository's data/raw/ ignore rule.

Before writing, the adapter recursively removes:

    apikey
    password
    savekey

The snapshot file is created with mode 0600.

The fetched snapshot is also passed through the existing canonical loadturn
importer and GameState validation. A snapshot is accepted only if that import
succeeds.

Console output contains only:

- game ID;
- turn;
- source player slot;
- entity/VCR counts;
- sanitized snapshot SHA256;
- local private path;
- canonical import status.

Raw private state is not included in runtime evidence.

## Candidate-site inspection

After fetching a snapshot, run:

    tools/run-private-turn-snapshot.sh candidate-sites --input <snapshot-path>

The inspector prints only sites that currently contain:

- at least one ship owned by the observing slot; and
- at least two visible ships owned by other slots.

For those sites it prints a compact ship/order projection:

    ship ID
    owner ID
    hull ID
    warp
    mission
    Primary Enemy
    Friendly Code
    damage
    crew
    name

This is intended only to choose or prepare a controlled prospective scenario.

## Prospective evidence discipline

Do not formulate another side rule from the private result and call the same
result validation.

Before the Host turn that will test the rule:

1. identify exact prize/captor/follow-up opponent IDs;
2. record the intended O/C topology;
3. freeze the expected result:

       capture side LEFT
       O pair not reachable
       C-forward continuation
       expected next prize side RIGHT

4. save the pre-Host private snapshot locally;
5. do not change the candidate after Host;
6. fetch the post-Host snapshot;
7. evaluate the VCR sequence against the frozen expectation.

Only a compact mechanics summary should be committed. Raw private loadturn
snapshots remain local.

## Security

Never pass the API key as a command-line argument.

A convenient interactive shell pattern is:

    read -rsp "Planets.nu API key: " PLANETSNU_API_KEY
    export PLANETSNU_API_KEY
    echo

After the fetch:

    unset PLANETSNU_API_KEY

The adapter does not persist the API key.

## Relationship to public100

Public100 remains an immutable exact-parity public corpus generation.

Private game 686764:

- is not added to public100;
- does not change public100 fingerprint;
- does not change CURRENT;
- is a prospective mechanics oracle only.
