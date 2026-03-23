## How it works

This chip implements a simple retro-inspired programmable sound generator. It provides two tone channels, a shared `3` bit envelope and a `1` bit audio output. Control data is loaded through SPI. All control registers are write only.

Tone generation uses a `23` bit phase accumulator for each channel. The phase value sets the pitch and drives the selected waveform. The shared envelope can be applied to either channel to shape its level.

### Pin connections

| Pin | Function |
| --- | --- |
| `ui_in[0]` | hard mute |
| `uo_out[7]` | audio output |
| `uio_in[0]` | `SPI_CS_N` |
| `uio_in[1]` | `SPI_MOSI` |
| `uio_in[3]` | `SPI_SCK` |

Unused pins:

- `uio_out` stays `0`
- `uio_oe` stays `0`
- all other user pins are unused

### Register map

| Address | Register | Description |
| --- | --- | --- |
| `0x0` | `CONTROL` | audio enable and register clear |
| `0x1` | `NOTE_A` | note value for channel A |
| `0x2` | `CHANNEL_A_CONTROL` | waveform and enable control for channel A |
| `0x3` | `NOTE_B` | note value for channel B |
| `0x4` | `CHANNEL_B_CONTROL` | waveform and enable control for channel B |
| `0x5` | `VOLUME_AB` | output level for both channels |
| `0x7` | `ENVELOPE_CONTROL` | envelope mode, restart and channel enable |
| `0x8` | `ENVELOPE_PERIOD` | envelope step period |

### Register description

#### `CONTROL`

| Bit | Description |
| --- | --- |
| `0` | audio enable |
| `1` | clear all stored register values |

#### `NOTE_A` and `NOTE_B`

| Bits | Description |
| --- | --- |
| `[6:4]` | octave |
| `[3:0]` | note select |

`NOTE_*[3:0] = 15` gives silence.

#### `CHANNEL_A_CONTROL` and `CHANNEL_B_CONTROL`

| Bits | Description |
| --- | --- |
| `[1:0]` | waveform select |
| `2` | tone enable |
| `4` | envelope enable for that channel |
| `5` | channel gate enable |

Waveform select:

| Value | Waveform |
| --- | --- |
| `0` | square |
| `1` | pulse |
| `2` | saw |
| `3` | triangle |

#### `VOLUME_AB`

| Bits | Description |
| --- | --- |
| `[2:0]` | channel A level |
| `[6:4]` | channel B level |

#### `ENVELOPE_CONTROL`

| Bit | Description |
| --- | --- |
| `0` | envelope mode select |
| `2` | envelope restart pulse when written as `1` |
| `3` | apply envelope to channel A |
| `4` | apply envelope to channel B |

Envelope mode select:

| Value | Mode |
| --- | --- |
| `0` | square |
| `1` | saw |

#### `ENVELOPE_PERIOD`

| Bits | Description |
| --- | --- |
| `[7:0]` | envelope step period |

Lower values give a faster envelope. Higher values give a slower
envelope.

### SPI transfer and timing

- project clock: `25_000_000 Hz`
- one SPI frame contains one command byte followed by one data byte
- keep `CS_N` low during the frame
- keep `SCK` low and high for at least `4` clock cycles each
- take `CS_N` low at least `4` clock cycles before the first `SCK` rising edge
- keep `CS_N` low at least `4` clock cycles after the last `SCK` falling edge
- keep `CS_N` high at least `4` clock cycles between frames

## How to test

A cocotb testbench is provided in `test/`

It can be executed with:

```sh
make -C test -B
```

## External hardware

- a Tiny Tapeout demo board, or another board that provides power and the project clock
- an SPI master for `SPI_CS_N`, `SPI_MOSI` and `SPI_SCK`
- for audio, use the TT Audio Pmod, or use a simple low-pass RC filter followed by an amplifier and speakers or headphones
