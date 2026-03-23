# SPDX-FileCopyrightText: © 2026 Peter Szentkuti
# SPDX-License-Identifier: Apache-2.0

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, ReadOnly, RisingEdge, Timer


# Clock and SPI timing used by the checks
CLK_PERIOD_NS = 40
SPI_MIN_HALF_PERIOD_CYCLES = 4
SPI_MIN_HALF_PERIOD_NS = CLK_PERIOD_NS * SPI_MIN_HALF_PERIOD_CYCLES
SPI_MIN_FRAME_GAP_NS = SPI_MIN_HALF_PERIOD_NS

# SPI pin positions on the shared port
SPI_CS_BIT = 0
SPI_MOSI_BIT = 1
SPI_SCK_BIT = 3

# Register addresses used by the live write map
REG_CONTROL = 0x0
REG_NOTE_A = 0x1
REG_CHANNEL_A_CONTROL = 0x2
REG_NOTE_B = 0x3
REG_CHANNEL_B_CONTROL = 0x4
REG_VOLUME_AB = 0x5
REG_NOISE_CONTROL = 0x6
REG_ENVELOPE_CONTROL = 0x7
REG_ENVELOPE_PERIOD = 0x8

ALL_WRITE_ADDRESSES = tuple(range(REG_ENVELOPE_PERIOD + 1))


# Small pin helpers
def set_spi_lines(dut, cs_n=1, sck=0, mosi=0):
    value = 0
    value |= (cs_n & 1) << SPI_CS_BIT
    value |= (mosi & 1) << SPI_MOSI_BIT
    value |= (sck & 1) << SPI_SCK_BIT
    dut.uio_in.value = value


def audio_value(dut):
    return (dut.uo_out.value.to_unsigned() >> 7) & 1


def quiet_output_bits(dut):
    return dut.uo_out.value.to_unsigned() & 0x7F


def uio_output_value(dut):
    return dut.uio_out.value.to_unsigned()


def uio_output_enable_value(dut):
    return dut.uio_oe.value.to_unsigned()


# Internal hierarchy helpers for RTL only checks
def psg_top(dut):
    return dut.user_project_u.mini_psg_top_u


def ctrl_top(dut):
    return psg_top(dut).mini_psg_control_top_u


def audio_top(dut):
    return psg_top(dut).mini_psg_audio_top_u


def gen_top(dut):
    return audio_top(dut).mini_psg_audio_generator_top_u


def out_top(dut):
    return audio_top(dut).mini_psg_audio_output_top_u


def reg_file(dut):
    return ctrl_top(dut).register_file_u


def note_lut_a(dut):
    return gen_top(dut).note_lut_a_u


def phase_accumulator_a(dut):
    return gen_top(dut).phase_accumulator_a_u


def waveform_a(dut):
    return gen_top(dut).waveform_generator_a_u


def noise_block(dut):
    return gen_top(dut).noise_generator_u


def envelope_block(dut):
    return gen_top(dut).envelope_generator_u


def volume_a(dut):
    return out_top(dut).volume_control_a_u


def mixer_block(dut):
    return out_top(dut).mixer_u


def dac_block(dut):
    return out_top(dut).dac_1bit_u


def control_hierarchy_is_visible(dut):
    try:
        _ = ctrl_top(dut)
        _ = reg_file(dut)
        return True
    except AttributeError:
        return False


def audio_hierarchy_is_visible(dut):
    try:
        _ = gen_top(dut)
        _ = out_top(dut)
        return True
    except AttributeError:
        return False


def byte_to_bits(value):
    return [((value >> bit_index) & 1) for bit_index in range(7, -1, -1)]


def new_bus_flags():
    return {
        "uio_output_seen": False,
        "uio_enable_seen": False,
    }


def sample_bus_flags(dut, bus_flags):
    bus_flags["uio_output_seen"] |= bool(uio_output_value(dut))
    bus_flags["uio_enable_seen"] |= bool(uio_output_enable_value(dut))


def assert_quiet_uio(bus_flags):
    assert not bus_flags["uio_output_seen"]
    assert not bus_flags["uio_enable_seen"]


# Expected register state for legal SPI traffic
def new_reg_state():
    return {
        REG_CONTROL: 0x00,
        REG_NOTE_A: 0x0F,
        REG_CHANNEL_A_CONTROL: 0x00,
        REG_NOTE_B: 0x0F,
        REG_CHANNEL_B_CONTROL: 0x00,
        REG_VOLUME_AB: 0x00,
        REG_NOISE_CONTROL: 0x00,
        REG_ENVELOPE_CONTROL: 0x00,
        REG_ENVELOPE_PERIOD: 0x10,
    }


def apply_reg_write(reg_state, address, data):
    if address == REG_CONTROL:
        reg_state[REG_CONTROL] = data & 0x01

        if data & 0x02:
            reg_state.update(new_reg_state())
    elif address == REG_NOTE_A:
        reg_state[REG_NOTE_A] = data & 0x7F
    elif address == REG_CHANNEL_A_CONTROL:
        reg_state[REG_CHANNEL_A_CONTROL] = data & 0x3F
    elif address == REG_NOTE_B:
        reg_state[REG_NOTE_B] = data & 0x7F
    elif address == REG_CHANNEL_B_CONTROL:
        reg_state[REG_CHANNEL_B_CONTROL] = data & 0x3F
    elif address == REG_VOLUME_AB:
        reg_state[REG_VOLUME_AB] = data & 0xFF
    elif address == REG_NOISE_CONTROL:
        reg_state[REG_NOISE_CONTROL] = data & 0x0F
    elif address == REG_ENVELOPE_CONTROL:
        reg_state[REG_ENVELOPE_CONTROL] = data & 0x1B
    elif address == REG_ENVELOPE_PERIOD:
        reg_state[REG_ENVELOPE_PERIOD] = data & 0xFF


def packed_envelope_control(reg_value):
    return (
        (((reg_value >> 4) & 1) << 3) |
        (((reg_value >> 3) & 1) << 2) |
        (reg_value & 0x03)
    )


def assert_control_state_matches(dut, reg_state):
    assert int(reg_file(dut).control_reg.value) == (reg_state[REG_CONTROL] & 0x01)
    assert reg_file(dut).note_a_reg.value.to_unsigned() == (reg_state[REG_NOTE_A] & 0x7F)
    assert reg_file(dut).channel_a_control_reg.value.to_unsigned() == (reg_state[REG_CHANNEL_A_CONTROL] & 0x3F)
    assert reg_file(dut).note_b_reg.value.to_unsigned() == (reg_state[REG_NOTE_B] & 0x7F)
    assert reg_file(dut).channel_b_control_reg.value.to_unsigned() == (reg_state[REG_CHANNEL_B_CONTROL] & 0x3F)
    assert reg_file(dut).volume_ab_reg.value.to_unsigned() == reg_state[REG_VOLUME_AB]
    assert reg_file(dut).noise_control_reg.value.to_unsigned() == (reg_state[REG_NOISE_CONTROL] & 0x0F)
    assert reg_file(dut).envelope_control_reg.value.to_unsigned() == packed_envelope_control(reg_state[REG_ENVELOPE_CONTROL])
    assert reg_file(dut).envelope_period_reg.value.to_unsigned() == reg_state[REG_ENVELOPE_PERIOD]


def scale_sample_level(sample_value, level_value):
    if level_value == 0x0:
        return 0
    if level_value == 0x1:
        return sample_value >> 4
    if level_value == 0x2:
        return sample_value >> 3
    if level_value == 0x3:
        return (sample_value >> 3) + (sample_value >> 4)
    if level_value == 0x4:
        return sample_value >> 2
    if level_value == 0x5:
        return (sample_value >> 2) + (sample_value >> 4)
    if level_value == 0x6:
        return (sample_value >> 2) + (sample_value >> 3)
    if level_value == 0x7:
        return (sample_value >> 2) + (sample_value >> 3) + (sample_value >> 4)
    if level_value == 0x8:
        return sample_value >> 1
    if level_value == 0x9:
        return (sample_value >> 1) + (sample_value >> 4)
    if level_value == 0xA:
        return (sample_value >> 1) + (sample_value >> 3)
    if level_value == 0xB:
        return (sample_value >> 1) + (sample_value >> 3) + (sample_value >> 4)
    if level_value == 0xC:
        return (sample_value >> 1) + (sample_value >> 2)
    if level_value == 0xD:
        return (sample_value >> 1) + (sample_value >> 2) + (sample_value >> 4)
    if level_value == 0xE:
        return (sample_value >> 1) + (sample_value >> 2) + (sample_value >> 3)
    if level_value == 0xF:
        return sample_value
    return 0


def saturate_mixed_sample(channel_a_value, channel_b_value):
    mixed_value = channel_a_value + channel_b_value

    if mixed_value > 255:
        return 255
    if mixed_value < -256:
        return -256
    return mixed_value


async def start_test_clock(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())


async def apply_reset(dut):
    dut.ena.value = 1
    dut.ui_in.value = 0
    set_spi_lines(dut, cs_n=1, sck=0, mosi=0)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 4)


async def wait_ns_if_needed(delay_ns):
    if delay_ns > 0:
        await Timer(delay_ns, unit="ns")


async def set_ui_value(dut, value):
    dut.ui_in.value = value & 0xFF
    await ClockCycles(dut.clk, 1)


async def spi_shift_bits_timed(dut, bit_values, cs_n, half_period_ns):
    bus_flags = new_bus_flags()

    for bit_value in bit_values:
        set_spi_lines(dut, cs_n=cs_n, sck=0, mosi=bit_value)
        await ReadOnly()
        sample_bus_flags(dut, bus_flags)
        await Timer(half_period_ns, unit="ns")

        set_spi_lines(dut, cs_n=cs_n, sck=1, mosi=bit_value)
        await ReadOnly()
        sample_bus_flags(dut, bus_flags)
        await Timer(half_period_ns, unit="ns")

        set_spi_lines(dut, cs_n=cs_n, sck=0, mosi=bit_value)
        await ReadOnly()
        sample_bus_flags(dut, bus_flags)
        await Timer(half_period_ns, unit="ns")

    return bus_flags


async def spi_transfer_byte_timed(dut, value, half_period_ns):
    return await spi_shift_bits_timed(
        dut,
        byte_to_bits(value),
        cs_n=0,
        half_period_ns=half_period_ns,
    )


async def spi_begin_frame(dut, setup_ns=SPI_MIN_HALF_PERIOD_NS):
    set_spi_lines(dut, cs_n=0, sck=0, mosi=0)
    await ReadOnly()
    await Timer(setup_ns, unit="ns")


async def spi_end_frame(dut, idle_ns=SPI_MIN_FRAME_GAP_NS):
    set_spi_lines(dut, cs_n=1, sck=0, mosi=0)
    await ReadOnly()

    bus_flags = new_bus_flags()
    sample_bus_flags(dut, bus_flags)

    await Timer(idle_ns, unit="ns")
    sample_bus_flags(dut, bus_flags)
    return bus_flags


async def spi_raw_frame_timed(
    dut,
    byte_values,
    half_period_ns=SPI_MIN_HALF_PERIOD_NS,
    setup_ns=SPI_MIN_HALF_PERIOD_NS,
    idle_ns=SPI_MIN_FRAME_GAP_NS,
):
    await spi_begin_frame(dut, setup_ns=setup_ns)

    byte_flags = []
    for value in byte_values:
        byte_flags.append(
            await spi_transfer_byte_timed(
                dut,
                value,
                half_period_ns=half_period_ns,
            )
        )

    frame_flags = await spi_end_frame(dut, idle_ns=idle_ns)
    return byte_flags, frame_flags


async def spi_raw_transaction_timed(
    dut,
    command_byte,
    data_byte,
    half_period_ns=SPI_MIN_HALF_PERIOD_NS,
):
    byte_flags, frame_flags = await spi_raw_frame_timed(
        dut,
        [command_byte, data_byte],
        half_period_ns=half_period_ns,
    )
    return byte_flags[0], byte_flags[1], frame_flags


async def spi_write_reg(dut, address, data, half_period_ns=SPI_MIN_HALF_PERIOD_NS):
    return await spi_raw_transaction_timed(
        dut,
        address & 0x0F,
        data & 0xFF,
        half_period_ns=half_period_ns,
    )


async def set_channel_a(dut, note_value, control_value, volume_value):
    await spi_write_reg(dut, REG_NOTE_A, note_value)
    await spi_write_reg(dut, REG_CHANNEL_A_CONTROL, control_value)
    await spi_write_reg(dut, REG_VOLUME_AB, volume_value)


async def set_channel_b(dut, note_value, control_value):
    await spi_write_reg(dut, REG_NOTE_B, note_value)
    await spi_write_reg(dut, REG_CHANNEL_B_CONTROL, control_value)


async def wait_for_condition(dut, condition, max_cycles=512):
    for _ in range(max_cycles):
        await RisingEdge(dut.clk)
        if condition():
            return

    raise AssertionError("condition was not met within the expected time")


async def drive_idle_bus_activity(dut, byte_values, half_period_ns=SPI_MIN_HALF_PERIOD_NS):
    bus_flags = new_bus_flags()

    for value in byte_values:
        shift_flags = await spi_shift_bits_timed(
            dut,
            byte_to_bits(value),
            cs_n=1,
            half_period_ns=half_period_ns,
        )
        bus_flags["uio_output_seen"] |= shift_flags["uio_output_seen"]
        bus_flags["uio_enable_seen"] |= shift_flags["uio_enable_seen"]

    return bus_flags


# Chip pin checks
@cocotb.test()
async def test_reset_defaults_keep_outputs_quiet(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    assert audio_value(dut) == 0
    assert quiet_output_bits(dut) == 0
    assert uio_output_value(dut) == 0
    assert uio_output_enable_value(dut) == 0

    if control_hierarchy_is_visible(dut):
        assert_control_state_matches(dut, new_reg_state())


@cocotb.test()
async def test_write_only_spi_keeps_uio_quiet(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    reg_state = new_reg_state()

    for address, value in (
        (REG_CONTROL, 0x05),
        (REG_NOTE_A, 0x10),
        (REG_CHANNEL_A_CONTROL, 0x24),
        (REG_NOTE_B, 0x33),
        (REG_CHANNEL_B_CONTROL, 0x2C),
        (REG_VOLUME_AB, 0x93),
        (REG_NOISE_CONTROL, 0x07),
        (REG_ENVELOPE_CONTROL, 0xFF),
        (REG_ENVELOPE_PERIOD, 0x08),
    ):
        command_flags, data_flags, frame_flags = await spi_write_reg(dut, address, value)
        assert_quiet_uio(command_flags)
        assert_quiet_uio(data_flags)
        assert_quiet_uio(frame_flags)
        apply_reg_write(reg_state, address, value)

    assert quiet_output_bits(dut) == 0
    assert uio_output_value(dut) == 0
    assert uio_output_enable_value(dut) == 0

    if control_hierarchy_is_visible(dut):
        assert_control_state_matches(dut, reg_state)


@cocotb.test()
async def test_invalid_write_command_is_ignored(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    reg_state = new_reg_state()

    for command_value in (0x10, 0x80, 0x90, 0xF0):
        command_flags, data_flags, frame_flags = await spi_raw_transaction_timed(
            dut,
            command_value,
            0xAA,
        )
        assert_quiet_uio(command_flags)
        assert_quiet_uio(data_flags)
        assert_quiet_uio(frame_flags)

    assert audio_value(dut) == 0
    assert quiet_output_bits(dut) == 0

    if control_hierarchy_is_visible(dut):
        assert_control_state_matches(dut, reg_state)


@cocotb.test()
async def test_soft_clear_restores_default_register_state(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    await spi_write_reg(dut, REG_CONTROL, 0x01)
    await spi_write_reg(dut, REG_NOTE_A, 0x7B)
    await spi_write_reg(dut, REG_CHANNEL_A_CONTROL, 0x24)
    await spi_write_reg(dut, REG_VOLUME_AB, 0x0F)

    audio_samples = []
    for _ in range(128):
        await RisingEdge(dut.clk)
        audio_samples.append(audio_value(dut))
    assert len(set(audio_samples)) > 1

    await spi_write_reg(dut, REG_CONTROL, 0x03)
    await ClockCycles(dut.clk, 4)

    assert audio_value(dut) == 0
    assert quiet_output_bits(dut) == 0

    if control_hierarchy_is_visible(dut):
        assert_control_state_matches(dut, new_reg_state())


@cocotb.test()
async def test_audio_output_follows_spi_writes_and_hard_mute(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    await spi_write_reg(dut, REG_CONTROL, 0x01)
    await set_channel_a(dut, note_value=0x7B, control_value=0x24, volume_value=0x0F)

    audio_samples = []
    quiet_bits = []
    for _ in range(256):
        await RisingEdge(dut.clk)
        audio_samples.append(audio_value(dut))
        quiet_bits.append(quiet_output_bits(dut))

    assert len(set(audio_samples)) > 1
    assert all(value == 0 for value in quiet_bits)

    await set_ui_value(dut, 0x01)
    await ClockCycles(dut.clk, 4)
    assert audio_value(dut) == 0
    assert quiet_output_bits(dut) == 0


@cocotb.test()
async def test_spi_single_frame_ignores_extra_bytes(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    byte_flags, frame_flags = await spi_raw_frame_timed(
        dut,
        [REG_NOTE_A, 0x22, 0x44],
    )
    for flags in byte_flags:
        assert_quiet_uio(flags)
    assert_quiet_uio(frame_flags)

    if control_hierarchy_is_visible(dut):
        assert ctrl_top(dut).note_a_value_o.value.to_unsigned() == 0x22


@cocotb.test()
async def test_min_timing_with_phase_sweep(dut):
    await start_test_clock(dut)

    for phase_offset_ns, value in zip((0, 5, 11, 19, 27, 35), (0x21, 0x32, 0x43, 0x54, 0x65, 0x76)):
        await apply_reset(dut)
        await wait_ns_if_needed(phase_offset_ns)

        for address, data in (
            (REG_NOTE_A, value),
            (REG_CHANNEL_A_CONTROL, 0x24),
            (REG_VOLUME_AB, 0x0F),
            (REG_CONTROL, 0x01),
        ):
            command_flags, data_flags, frame_flags = await spi_write_reg(
                dut,
                address,
                data,
                half_period_ns=SPI_MIN_HALF_PERIOD_NS,
            )
            assert_quiet_uio(command_flags)
            assert_quiet_uio(data_flags)
            assert_quiet_uio(frame_flags)

        audio_samples = []
        for _ in range(128):
            await RisingEdge(dut.clk)
            audio_samples.append(audio_value(dut))

        assert len(set(audio_samples)) > 1


@cocotb.test()
async def test_cs_abort_mid_command_is_ignored(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    await spi_begin_frame(dut)
    phase_flags = await spi_shift_bits_timed(
        dut,
        byte_to_bits(REG_NOTE_A)[:4],
        cs_n=0,
        half_period_ns=SPI_MIN_HALF_PERIOD_NS,
    )
    assert_quiet_uio(phase_flags)
    end_flags = await spi_end_frame(dut)
    assert_quiet_uio(end_flags)

    if control_hierarchy_is_visible(dut):
        assert_control_state_matches(dut, new_reg_state())

    await spi_write_reg(dut, REG_NOTE_A, 0x2A)
    if control_hierarchy_is_visible(dut):
        assert ctrl_top(dut).note_a_value_o.value.to_unsigned() == 0x2A


@cocotb.test()
async def test_cs_abort_mid_data_is_ignored(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    await spi_begin_frame(dut)
    command_flags = await spi_transfer_byte_timed(dut, REG_NOTE_A, SPI_MIN_HALF_PERIOD_NS)
    assert_quiet_uio(command_flags)
    phase_flags = await spi_shift_bits_timed(
        dut,
        byte_to_bits(0xA0)[:4],
        cs_n=0,
        half_period_ns=SPI_MIN_HALF_PERIOD_NS,
    )
    assert_quiet_uio(phase_flags)
    end_flags = await spi_end_frame(dut)
    assert_quiet_uio(end_flags)

    if control_hierarchy_is_visible(dut):
        assert_control_state_matches(dut, new_reg_state())

    await spi_write_reg(dut, REG_NOTE_A, 0x7C)
    if control_hierarchy_is_visible(dut):
        assert ctrl_top(dut).note_a_value_o.value.to_unsigned() == 0x7C


@cocotb.test()
async def test_spi_ignores_activity_while_cs_high(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    phase_flags = await drive_idle_bus_activity(
        dut,
        [0xAA, 0x55, 0xF0],
        half_period_ns=SPI_MIN_HALF_PERIOD_NS,
    )
    assert_quiet_uio(phase_flags)
    assert audio_value(dut) == 0

    if control_hierarchy_is_visible(dut):
        assert_control_state_matches(dut, new_reg_state())


@cocotb.test()
async def test_random_legal_spi_traffic_matches_register_model(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not control_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only register check because the internal control hierarchy is not visible")
        return

    rng = random.Random(20260323)
    reg_state = new_reg_state()

    for _ in range(40):
        await wait_ns_if_needed(rng.randrange(0, CLK_PERIOD_NS))
        half_period_ns = SPI_MIN_HALF_PERIOD_NS + rng.randrange(0, 5) * 20
        address = rng.choice(ALL_WRITE_ADDRESSES)
        data = rng.randrange(0, 256)

        command_flags, data_flags, frame_flags = await spi_write_reg(
            dut,
            address,
            data,
            half_period_ns=half_period_ns,
        )
        assert_quiet_uio(command_flags)
        assert_quiet_uio(data_flags)
        assert_quiet_uio(frame_flags)

        apply_reg_write(reg_state, address, data)
        assert_control_state_matches(dut, reg_state)


# Audio path checks
@cocotb.test()
async def test_note_path_gate_and_rest_are_cleanly_muted(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not audio_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only audio check because the internal audio hierarchy is not visible")
        return

    await spi_write_reg(dut, REG_CONTROL, 0x01)
    await set_channel_a(dut, note_value=0x10, control_value=0x24, volume_value=0x0F)

    expected_step = 22 << 1
    assert gen_top(dut).channel_a_phase_step.value.to_unsigned() == expected_step

    phase_before = gen_top(dut).channel_a_phase_value.value.to_unsigned()
    await ClockCycles(dut.clk, 4)
    phase_after = gen_top(dut).channel_a_phase_value.value.to_unsigned()
    assert int(gen_top(dut).channel_a_tone_enable.value) == 1
    assert phase_after != phase_before
    assert gen_top(dut).channel_a_wave_sample.value.to_signed() != 0

    await spi_write_reg(dut, REG_CHANNEL_A_CONTROL, 0x04)
    frozen_phase = gen_top(dut).channel_a_phase_value.value.to_unsigned()
    await ClockCycles(dut.clk, 4)
    assert gen_top(dut).channel_a_phase_value.value.to_unsigned() == frozen_phase
    assert gen_top(dut).channel_a_source_sample_o.value.to_signed() == 0

    await spi_write_reg(dut, REG_CHANNEL_A_CONTROL, 0x20)
    await ClockCycles(dut.clk, 2)
    assert gen_top(dut).channel_a_source_sample_o.value.to_signed() == 0

    await spi_write_reg(dut, REG_NOTE_A, 0x0F)
    await spi_write_reg(dut, REG_CHANNEL_A_CONTROL, 0x24)
    await ClockCycles(dut.clk, 2)
    assert gen_top(dut).channel_a_phase_step.value.to_unsigned() == 0
    assert gen_top(dut).channel_a_source_sample_o.value.to_signed() == 0


@cocotb.test()
async def test_control_outputs_follow_register_writes(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not control_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only control check because the internal control hierarchy is not visible")
        return

    await spi_write_reg(dut, REG_CONTROL, 0x01)
    await ClockCycles(dut.clk, 2)
    assert int(ctrl_top(dut).audio_enable_o.value) == 1
    assert int(reg_file(dut).control_reg.value) == 1

    await spi_write_reg(dut, REG_ENVELOPE_CONTROL, 0x0D)
    assert reg_file(dut).envelope_control_reg.value.to_unsigned() == 0x05

    await spi_write_reg(dut, REG_CONTROL, 0x03)
    await ClockCycles(dut.clk, 2)
    assert int(ctrl_top(dut).audio_enable_o.value) == 0
    assert int(reg_file(dut).control_reg.value) == 0


@cocotb.test()
async def test_note_lut_and_phase_accumulator_values(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not audio_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only audio check because the internal audio hierarchy is not visible")
        return

    await spi_write_reg(dut, REG_NOTE_A, 0x00)
    await ClockCycles(dut.clk, 2)
    assert note_lut_a(dut).phase_step_o.value.to_unsigned() == 22

    await spi_write_reg(dut, REG_NOTE_A, 0x10)
    await ClockCycles(dut.clk, 2)
    assert note_lut_a(dut).phase_step_o.value.to_unsigned() == 44

    await spi_write_reg(dut, REG_NOTE_A, 0x2B)
    await ClockCycles(dut.clk, 2)
    assert note_lut_a(dut).phase_step_o.value.to_unsigned() == (41 << 2)

    await spi_write_reg(dut, REG_NOTE_A, 0x8F)
    await ClockCycles(dut.clk, 2)
    assert note_lut_a(dut).phase_step_o.value.to_unsigned() == 0

    await spi_write_reg(dut, REG_NOTE_A, 0x10)
    await spi_write_reg(dut, REG_CHANNEL_A_CONTROL, 0x24)
    await ClockCycles(dut.clk, 2)
    assert phase_accumulator_a(dut).phase_value_o.value.to_unsigned() == 0

    await spi_write_reg(dut, REG_CONTROL, 0x01)
    phase_values = []
    for _ in range(5):
        await RisingEdge(dut.clk)
        phase_values.append(phase_accumulator_a(dut).phase_value_o.value.to_unsigned())
    phase_steps = [right - left for left, right in zip(phase_values, phase_values[1:])]
    assert phase_steps == [44, 44, 44, 44]

    await spi_write_reg(dut, REG_CHANNEL_A_CONTROL, 0x04)
    frozen_phase = phase_accumulator_a(dut).phase_value_o.value.to_unsigned()
    await ClockCycles(dut.clk, 4)
    assert phase_accumulator_a(dut).phase_value_o.value.to_unsigned() == frozen_phase

    await spi_write_reg(dut, REG_CONTROL, 0x03)
    await ClockCycles(dut.clk, 2)
    assert phase_accumulator_a(dut).phase_value_o.value.to_unsigned() == 0


@cocotb.test()
async def test_waveform_generator_builds_all_shapes(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not audio_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only audio check because the internal audio hierarchy is not visible")
        return

    await spi_write_reg(dut, REG_NOTE_A, 0x7B)
    await spi_write_reg(dut, REG_CHANNEL_A_CONTROL, 0x24)
    await spi_write_reg(dut, REG_CONTROL, 0x01)

    square_samples = []
    for _ in range(4096):
        await RisingEdge(dut.clk)
        square_samples.append(waveform_a(dut).sample_out_o.value.to_signed())
    assert set(square_samples) == {-96, 96}

    await spi_write_reg(dut, REG_CHANNEL_A_CONTROL, 0x25)
    pulse_samples = []
    for _ in range(4096):
        await RisingEdge(dut.clk)
        pulse_samples.append(waveform_a(dut).sample_out_o.value.to_signed())
    assert set(pulse_samples) == {-96, 96}
    assert pulse_samples.count(-96) > pulse_samples.count(96)

    await spi_write_reg(dut, REG_CHANNEL_A_CONTROL, 0x26)
    saw_samples = []
    for _ in range(4096):
        await RisingEdge(dut.clk)
        saw_samples.append(waveform_a(dut).sample_out_o.value.to_signed())
    assert len(set(saw_samples)) > 16
    assert max(saw_samples) > 0
    assert min(saw_samples) < 0

    await spi_write_reg(dut, REG_CHANNEL_A_CONTROL, 0x27)
    triangle_samples = []
    for _ in range(4096):
        await RisingEdge(dut.clk)
        triangle_samples.append(waveform_a(dut).sample_out_o.value.to_signed())
    assert max(triangle_samples) >= 60
    assert min(triangle_samples) <= -60


@cocotb.test()
async def test_noise_generator_enable_clear_and_disable(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not audio_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only audio check because the internal audio hierarchy is not visible")
        return

    await spi_write_reg(dut, REG_CHANNEL_A_CONTROL, 0x28)
    await spi_write_reg(dut, REG_NOISE_CONTROL, 0x03)
    await spi_write_reg(dut, REG_CONTROL, 0x01)

    noise_bits = []
    noise_samples = []
    for _ in range(128):
        await RisingEdge(dut.clk)
        noise_bits.append(int(noise_block(dut).noise_bit_o.value))
        noise_samples.append(noise_block(dut).noise_sample_o.value.to_signed())

    assert len(set(noise_bits)) > 1
    assert any(value != 0 for value in noise_samples)

    await spi_write_reg(dut, REG_NOISE_CONTROL, 0x00)
    await ClockCycles(dut.clk, 4)
    assert int(gen_top(dut).channel_a_noise_enable.value) == 0
    assert noise_block(dut).noise_sample_o.value.to_signed() == 0

    await spi_write_reg(dut, REG_CONTROL, 0x03)
    await ClockCycles(dut.clk, 2)
    assert noise_block(dut).lfsr_reg.value.to_unsigned() == 0x0001
    assert noise_block(dut).divider_reg.value.to_unsigned() == 3


@cocotb.test()
async def test_envelope_generator_modes_and_restart(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not audio_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only audio check because the internal audio hierarchy is not visible")
        return

    await spi_write_reg(dut, REG_CONTROL, 0x01)
    await spi_write_reg(dut, REG_ENVELOPE_PERIOD, 0x01)

    await spi_write_reg(dut, REG_ENVELOPE_CONTROL, 0x0C)
    hold_levels = []
    for _ in range(8):
        await RisingEdge(dut.clk)
        hold_levels.append(envelope_block(dut).envelope_level_o.value.to_unsigned())
    assert hold_levels == [0xF] * 8

    await spi_write_reg(dut, REG_ENVELOPE_CONTROL, 0x0D)
    decay_levels = []
    for _ in range(8):
        await RisingEdge(dut.clk)
        decay_levels.append(envelope_block(dut).envelope_level_o.value.to_unsigned())
    assert decay_levels[0] >= decay_levels[-1]
    assert all(left >= right for left, right in zip(decay_levels, decay_levels[1:]))
    assert decay_levels[-1] < 0xF

    rise_fall_write = cocotb.start_soon(spi_write_reg(dut, REG_ENVELOPE_CONTROL, 0x0E))
    rise_fall_levels = []
    for _ in range(256):
        await RisingEdge(dut.clk)
        rise_fall_levels.append(envelope_block(dut).envelope_level_o.value.to_unsigned())
    await rise_fall_write
    rise_fall_start = rise_fall_levels.index(min(rise_fall_levels))
    rise_fall_tail = rise_fall_levels[rise_fall_start:]
    rise_fall_steps = [right - left for left, right in zip(rise_fall_tail, rise_fall_tail[1:])]
    assert max(rise_fall_tail) > min(rise_fall_tail)
    assert any(step > 0 for step in rise_fall_steps)
    assert any(step < 0 for step in rise_fall_steps)

    loop_write = cocotb.start_soon(spi_write_reg(dut, REG_ENVELOPE_CONTROL, 0x0F))
    loop_levels = []
    for _ in range(320):
        await RisingEdge(dut.clk)
        loop_levels.append(envelope_block(dut).envelope_level_o.value.to_unsigned())
    await loop_write
    loop_start = loop_levels.index(min(loop_levels))
    loop_tail = loop_levels[loop_start:]
    level_steps = [right - left for left, right in zip(loop_tail, loop_tail[1:])]
    assert min(loop_tail) == 0
    assert max(loop_tail) == 0xF
    assert any(step > 0 for step in level_steps)
    assert any(step < 0 for step in level_steps)


@cocotb.test()
async def test_volume_control_and_mixer_follow_levels(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not audio_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only audio check because the internal audio hierarchy is not visible")
        return

    await spi_write_reg(dut, REG_NOTE_A, 0x7B)
    await spi_write_reg(dut, REG_CHANNEL_A_CONTROL, 0x24)
    await spi_write_reg(dut, REG_VOLUME_AB, 0x05)
    await spi_write_reg(dut, REG_CONTROL, 0x01)

    for _ in range(32):
        await RisingEdge(dut.clk)
        channel_a_source = gen_top(dut).channel_a_source_sample_o.value.to_signed()
        channel_a_scaled = out_top(dut).channel_a_scaled_sample.value.to_signed()
        mixed_sample = mixer_block(dut).mixed_sample_o.value.to_signed()
        expected_scaled = scale_sample_level(channel_a_source, 0x5)
        expected_mixed = saturate_mixed_sample(expected_scaled, 0)
        assert channel_a_scaled == expected_scaled
        assert mixed_sample == expected_mixed

    await spi_write_reg(dut, REG_CHANNEL_A_CONTROL, 0x34)
    await spi_write_reg(dut, REG_ENVELOPE_PERIOD, 0x01)
    await spi_write_reg(dut, REG_ENVELOPE_CONTROL, 0x0D)

    for _ in range(16):
        await RisingEdge(dut.clk)
        channel_a_source = gen_top(dut).channel_a_source_sample_o.value.to_signed()
        envelope_level = envelope_block(dut).envelope_level_o.value.to_unsigned()
        channel_a_scaled = volume_a(dut).sample_out_o.value.to_signed()
        assert channel_a_scaled == scale_sample_level(channel_a_source, envelope_level)

    await apply_reset(dut)
    await spi_write_reg(dut, REG_NOTE_A, 0x7B)
    await spi_write_reg(dut, REG_CHANNEL_A_CONTROL, 0x2C)
    await spi_write_reg(dut, REG_NOTE_B, 0x7B)
    await spi_write_reg(dut, REG_CHANNEL_B_CONTROL, 0x2C)
    await spi_write_reg(dut, REG_VOLUME_AB, 0xFF)
    await spi_write_reg(dut, REG_NOISE_CONTROL, 0x03)
    await spi_write_reg(dut, REG_CONTROL, 0x01)

    await wait_for_condition(
        dut,
        lambda: mixer_block(dut).mixed_sample_o.value.to_signed() == 255,
        max_cycles=4096,
    )
    await wait_for_condition(
        dut,
        lambda: mixer_block(dut).mixed_sample_o.value.to_signed() == -256,
        max_cycles=4096,
    )


@cocotb.test()
async def test_dac_and_audio_output_drive_activity(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not audio_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only audio check because the internal audio hierarchy is not visible")
        return

    await spi_write_reg(dut, REG_NOTE_A, 0x7B)
    await spi_write_reg(dut, REG_CHANNEL_A_CONTROL, 0x24)
    await spi_write_reg(dut, REG_VOLUME_AB, 0x0F)
    await spi_write_reg(dut, REG_CONTROL, 0x01)

    raw_audio_values = []
    top_audio_values = []
    quiet_bits = []
    for _ in range(128):
        await RisingEdge(dut.clk)
        raw_audio_values.append(int(dac_block(dut).audio_o.value))
        top_audio_values.append(audio_value(dut))
        quiet_bits.append(quiet_output_bits(dut))

    assert len(set(raw_audio_values)) > 1
    assert len(set(top_audio_values)) > 1
    assert all(value == 0 for value in quiet_bits)

    await set_ui_value(dut, 0x01)
    await ClockCycles(dut.clk, 4)
    assert audio_value(dut) == 0

    await set_ui_value(dut, 0x00)
    await spi_write_reg(dut, REG_CONTROL, 0x03)
    await ClockCycles(dut.clk, 2)
    assert audio_value(dut) == 0
    assert int(ctrl_top(dut).audio_enable_o.value) == 0


@cocotb.test()
async def test_channel_b_envelope_enable_and_hard_mute(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not audio_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only audio check because the internal audio hierarchy is not visible")
        return

    await spi_write_reg(dut, REG_CONTROL, 0x01)
    await spi_write_reg(dut, REG_NOTE_B, 0x7B)
    await spi_write_reg(dut, REG_CHANNEL_B_CONTROL, 0x34)
    await spi_write_reg(dut, REG_VOLUME_AB, 0xF0)
    await spi_write_reg(dut, REG_ENVELOPE_PERIOD, 0x20)
    await spi_write_reg(dut, REG_ENVELOPE_CONTROL, 0x15)

    assert reg_file(dut).envelope_control_reg.value.to_unsigned() == 0x09
    assert int(gen_top(dut).channel_b_envelope_enable_o.value) == 1

    scaled_samples = []
    envelope_levels = []
    for _ in range(128):
        await RisingEdge(dut.clk)
        scaled_samples.append(out_top(dut).channel_b_scaled_sample.value.to_signed())
        envelope_levels.append(audio_top(dut).envelope_level.value.to_unsigned())

    non_zero_scaled = {value for value in scaled_samples if value != 0}
    assert len(set(envelope_levels)) > 1
    assert len(non_zero_scaled) > 1

    await set_ui_value(dut, 0x01)
    await ClockCycles(dut.clk, 4)
    assert audio_value(dut) == 0

    await set_ui_value(dut, 0x00)
    await ClockCycles(dut.clk, 4)
    assert audio_value(dut) in (0, 1)
