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
HARD_MUTE_SYNC_CYCLES = 2

# SPI pin positions on the shared port
SPI_CS_BIT = 0
SPI_MOSI_BIT = 1
SPI_SCK_BIT = 2

# Register addresses used by the live write map
REG_CONTROL = 0x0
REG_NOTE_A = 0x1
REG_CHANNEL_A_CONTROL = 0x2
REG_NOTE_B = 0x3
REG_CHANNEL_B_CONTROL = 0x4
REG_VOLUME_AB = 0x5
REG_ENVELOPE_CONTROL = 0x7
REG_ENVELOPE_PERIOD = 0x8
ACTIVE_TEST_NOTE = 0x79

ALL_WRITE_ADDRESSES = (
    REG_CONTROL,
    REG_NOTE_A,
    REG_CHANNEL_A_CONTROL,
    REG_NOTE_B,
    REG_CHANNEL_B_CONTROL,
    REG_VOLUME_AB,
    REG_ENVELOPE_CONTROL,
    REG_ENVELOPE_PERIOD,
)


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


def core_reset_n(dut):
    return int(psg_top(dut).rst_ni.value)


def ctrl_top(dut):
    return psg_top(dut).mini_psg_control_top_u


def audio_top(dut):
    return psg_top(dut).mini_psg_audio_top_u


def gen_top(dut):
    return audio_top(dut).mini_psg_audio_generator_top_u


def out_top(dut):
    return audio_top(dut).mini_psg_audio_output_top_u


def hard_mute_sync_state(dut):
    return out_top(dut).hard_mute_sync_q.value.to_unsigned()


def reg_file(dut):
    return ctrl_top(dut).register_file_u


def note_lut_a(dut):
    return gen_top(dut).note_lut_a_u


def phase_accumulator_a(dut):
    return gen_top(dut).phase_accumulator_a_u


def waveform_a(dut):
    return gen_top(dut).waveform_generator_a_u


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


def reset_hierarchy_is_visible(dut):
    try:
        _ = psg_top(dut).rst_ni
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


async def sample_signal_for_cycles(dut, signal_getter, cycle_count):
    samples = []
    for _ in range(cycle_count):
        await RisingEdge(dut.clk)
        samples.append(signal_getter())
    return samples


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
        reg_state[REG_CHANNEL_A_CONTROL] = data & 0x37
    elif address == REG_NOTE_B:
        reg_state[REG_NOTE_B] = data & 0x7F
    elif address == REG_CHANNEL_B_CONTROL:
        reg_state[REG_CHANNEL_B_CONTROL] = data & 0x37
    elif address == REG_VOLUME_AB:
        reg_state[REG_VOLUME_AB] = data & 0x77
    elif address == REG_ENVELOPE_CONTROL:
        reg_state[REG_ENVELOPE_CONTROL] = data & 0x19
    elif address == REG_ENVELOPE_PERIOD:
        reg_state[REG_ENVELOPE_PERIOD] = data & 0xFF


def packed_envelope_control(reg_value):
    return (
        (((reg_value >> 4) & 1) << 2) |
        (((reg_value >> 3) & 1) << 1) |
        (reg_value & 0x01)
    )


def assert_control_state_matches(dut, reg_state):
    assert int(reg_file(dut).control_reg.value) == (reg_state[REG_CONTROL] & 0x01)
    assert reg_file(dut).note_a_reg.value.to_unsigned() == (reg_state[REG_NOTE_A] & 0x7F)
    assert reg_file(dut).channel_a_control_reg.value.to_unsigned() == (
        (((reg_state[REG_CHANNEL_A_CONTROL] >> 5) & 1) << 4) |
        (((reg_state[REG_CHANNEL_A_CONTROL] >> 4) & 1) << 3) |
        (((reg_state[REG_CHANNEL_A_CONTROL] >> 2) & 1) << 2) |
        (reg_state[REG_CHANNEL_A_CONTROL] & 0x03)
    )
    assert reg_file(dut).note_b_reg.value.to_unsigned() == (reg_state[REG_NOTE_B] & 0x7F)
    assert reg_file(dut).channel_b_control_reg.value.to_unsigned() == (
        (((reg_state[REG_CHANNEL_B_CONTROL] >> 5) & 1) << 4) |
        (((reg_state[REG_CHANNEL_B_CONTROL] >> 4) & 1) << 3) |
        (((reg_state[REG_CHANNEL_B_CONTROL] >> 2) & 1) << 2) |
        (reg_state[REG_CHANNEL_B_CONTROL] & 0x03)
    )
    assert reg_file(dut).volume_ab_reg.value.to_unsigned() == (
        (((reg_state[REG_VOLUME_AB] >> 4) & 0x07) << 3) |
        (reg_state[REG_VOLUME_AB] & 0x07)
    )
    assert reg_file(dut).envelope_control_reg.value.to_unsigned() == packed_envelope_control(reg_state[REG_ENVELOPE_CONTROL])
    assert reg_file(dut).envelope_period_reg.value.to_unsigned() == reg_state[REG_ENVELOPE_PERIOD]


def scale_sample_level(sample_value, level_value):
    if level_value == 0x0:
        return 0
    if level_value == 0x1:
        return sample_value >> 3
    if level_value == 0x2:
        return sample_value >> 2
    if level_value == 0x3:
        return (sample_value >> 2) + (sample_value >> 3)
    if level_value == 0x4:
        return sample_value >> 1
    if level_value == 0x5:
        return (sample_value >> 1) + (sample_value >> 3)
    if level_value == 0x6:
        return (sample_value >> 1) + (sample_value >> 2)
    if level_value == 0x7:
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
async def test_internal_reset_release_is_synchronized_to_clk(dut):
    await start_test_clock(dut)

    if not reset_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only reset check because the internal reset hierarchy is not visible")
        return

    dut.ena.value = 1
    dut.ui_in.value = 0
    set_spi_lines(dut, cs_n=1, sck=0, mosi=0)
    dut.rst_n.value = 0

    await ReadOnly()
    assert core_reset_n(dut) == 0

    await ClockCycles(dut.clk, 3)
    await ReadOnly()
    assert core_reset_n(dut) == 0

    await Timer(1, unit="ns")
    dut.rst_n.value = 1
    await ReadOnly()
    assert core_reset_n(dut) == 0

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert core_reset_n(dut) == 0

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert core_reset_n(dut) == 1

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
        (REG_VOLUME_AB, 0x53),
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
    await spi_write_reg(dut, REG_NOTE_A, ACTIVE_TEST_NOTE)
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
    await set_channel_a(dut, note_value=ACTIVE_TEST_NOTE, control_value=0x24, volume_value=0x0F)

    audio_samples = []
    quiet_bits = []
    for _ in range(256):
        await RisingEdge(dut.clk)
        audio_samples.append(audio_value(dut))
        quiet_bits.append(quiet_output_bits(dut))

    assert len(set(audio_samples)) > 1
    assert all(value == 0 for value in quiet_bits)

    await set_ui_value(dut, 0x01)
    await ClockCycles(dut.clk, HARD_MUTE_SYNC_CYCLES + 2)
    muted_audio = await sample_signal_for_cycles(dut, lambda: audio_value(dut), 16)
    assert set(muted_audio) == {0}
    assert quiet_output_bits(dut) == 0

    await set_ui_value(dut, 0x00)
    resumed_audio = await sample_signal_for_cycles(dut, lambda: audio_value(dut), 128)
    assert len(set(resumed_audio)) > 1


@cocotb.test()
async def test_hard_mute_clears_dac_state_before_release(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not audio_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only audio check because the internal audio hierarchy is not visible")
        return

    await spi_write_reg(dut, REG_CONTROL, 0x01)
    await set_channel_a(dut, note_value=ACTIVE_TEST_NOTE, control_value=0x24, volume_value=0x0F)

    raw_before_mute = await sample_signal_for_cycles(
        dut,
        lambda: int(dac_block(dut).audio_o.value),
        128,
    )
    assert len(set(raw_before_mute)) > 1

    await RisingEdge(dut.clk)
    dut.ui_in.value = 0x01
    await ReadOnly()
    assert hard_mute_sync_state(dut) == 0x0
    assert audio_value(dut) == int(dac_block(dut).audio_o.value)

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert hard_mute_sync_state(dut) == 0x1
    assert audio_value(dut) == int(dac_block(dut).audio_o.value)

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert hard_mute_sync_state(dut) == 0x3
    assert audio_value(dut) == 0

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert audio_value(dut) == 0
    assert int(dac_block(dut).audio_o.value) == 0
    assert dac_block(dut).error_reg.value.to_signed() == 0

    muted_top_samples = []
    muted_raw_samples = []
    muted_error_values = []
    for _ in range(32):
        await RisingEdge(dut.clk)
        muted_top_samples.append(audio_value(dut))
        muted_raw_samples.append(int(dac_block(dut).audio_o.value))
        muted_error_values.append(dac_block(dut).error_reg.value.to_signed())

    assert set(muted_top_samples) == {0}
    assert set(muted_raw_samples) == {0}
    assert set(muted_error_values) == {0}

    await RisingEdge(dut.clk)
    dut.ui_in.value = 0x00
    await ReadOnly()
    assert hard_mute_sync_state(dut) == 0x3

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert hard_mute_sync_state(dut) == 0x2
    assert audio_value(dut) == 0
    assert int(dac_block(dut).audio_o.value) == 0
    assert dac_block(dut).error_reg.value.to_signed() == 0

    await RisingEdge(dut.clk)
    await ReadOnly()
    assert hard_mute_sync_state(dut) == 0x0
    assert audio_value(dut) == 0
    assert int(dac_block(dut).audio_o.value) == 0
    assert dac_block(dut).error_reg.value.to_signed() == 0

    resumed_top_samples = []
    resumed_raw_samples = []
    for _ in range(8):
        await RisingEdge(dut.clk)
        resumed_top_samples.append(audio_value(dut))
        resumed_raw_samples.append(int(dac_block(dut).audio_o.value))

    assert resumed_top_samples[:2] == [0, 0]
    assert resumed_top_samples == resumed_raw_samples

    activity_after_release = await sample_signal_for_cycles(
        dut,
        lambda: audio_value(dut),
        128,
    )
    assert len(set(activity_after_release)) > 1


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
async def test_unmapped_write_addresses_are_ignored(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not control_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only control check because the internal control hierarchy is not visible")
        return

    reg_state = new_reg_state()

    await spi_write_reg(dut, REG_NOTE_A, 0x2A)
    apply_reg_write(reg_state, REG_NOTE_A, 0x2A)
    assert_control_state_matches(dut, reg_state)

    for address in (0x6, 0x9, 0xA, 0xE, 0xF):
        await spi_write_reg(dut, address, 0xFF)
        assert_control_state_matches(dut, reg_state)


@cocotb.test()
async def test_write_masks_unused_bits_before_store(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not control_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only control check because the internal control hierarchy is not visible")
        return

    reg_state = new_reg_state()

    for address, data in (
        (REG_CONTROL, 0x05),
        (REG_NOTE_A, 0xFF),
        (REG_CHANNEL_A_CONTROL, 0xFF),
        (REG_NOTE_B, 0xFF),
        (REG_CHANNEL_B_CONTROL, 0xFF),
        (REG_VOLUME_AB, 0xFF),
        (REG_ENVELOPE_CONTROL, 0xFF),
        (REG_ENVELOPE_PERIOD, 0xFF),
    ):
        await spi_write_reg(dut, address, data)
        apply_reg_write(reg_state, address, data)
        assert_control_state_matches(dut, reg_state)


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
async def test_note_path_gate_and_no_tone_codes_are_cleanly_muted(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not audio_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only audio check because the internal audio hierarchy is not visible")
        return

    await spi_write_reg(dut, REG_CONTROL, 0x01)
    await set_channel_a(dut, note_value=0x10, control_value=0x24, volume_value=0x0F)

    expected_step = 11 << 1
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
    assert reg_file(dut).envelope_control_reg.value.to_unsigned() == 0x03

    await spi_write_reg(dut, REG_CONTROL, 0x03)
    await ClockCycles(dut.clk, 2)
    assert int(ctrl_top(dut).audio_enable_o.value) == 0
    assert int(reg_file(dut).control_reg.value) == 0


@cocotb.test()
async def test_control_pulses_are_single_cycle(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not control_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only control check because the internal control hierarchy is not visible")
        return

    await spi_write_reg(dut, REG_CONTROL, 0x01)

    clear_task = cocotb.start_soon(spi_write_reg(dut, REG_CONTROL, 0x03))
    clear_samples = await sample_signal_for_cycles(
        dut,
        lambda: int(ctrl_top(dut).clear_enable_o.value),
        260,
    )
    await clear_task

    assert sum(clear_samples) == 1
    assert int(ctrl_top(dut).clear_enable_o.value) == 0
    assert int(ctrl_top(dut).audio_enable_o.value) == 0
    assert int(reg_file(dut).control_reg.value) == 0

    await spi_write_reg(dut, REG_CONTROL, 0x01)

    restart_task = cocotb.start_soon(spi_write_reg(dut, REG_ENVELOPE_CONTROL, 0x0D))
    restart_samples = await sample_signal_for_cycles(
        dut,
        lambda: int(ctrl_top(dut).envelope_restart_pulse_o.value),
        260,
    )
    await restart_task

    assert sum(restart_samples) == 1
    assert int(ctrl_top(dut).envelope_restart_pulse_o.value) == 0
    assert reg_file(dut).envelope_control_reg.value.to_unsigned() == 0x03


@cocotb.test()
async def test_note_lut_and_phase_accumulator_values(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not audio_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only audio check because the internal audio hierarchy is not visible")
        return

    expected_base_steps = [11, 12, 13, 14, 15, 16, 17, 18, 20, 21]

    await spi_write_reg(dut, REG_NOTE_A, 0x00)
    await ClockCycles(dut.clk, 2)
    assert note_lut_a(dut).phase_step_o.value.to_unsigned() == 11

    for note_index, expected_step in enumerate(expected_base_steps):
        await spi_write_reg(dut, REG_NOTE_A, note_index)
        await ClockCycles(dut.clk, 2)
        assert note_lut_a(dut).phase_step_o.value.to_unsigned() == expected_step

    await spi_write_reg(dut, REG_NOTE_A, 0x10)
    await ClockCycles(dut.clk, 2)
    assert note_lut_a(dut).phase_step_o.value.to_unsigned() == 22

    await spi_write_reg(dut, REG_NOTE_A, 0x29)
    await ClockCycles(dut.clk, 2)
    assert note_lut_a(dut).phase_step_o.value.to_unsigned() == (21 << 2)

    await spi_write_reg(dut, REG_NOTE_A, 0x8F)
    await ClockCycles(dut.clk, 2)
    assert note_lut_a(dut).phase_step_o.value.to_unsigned() == 0

    for note_index in (0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F):
        await spi_write_reg(dut, REG_NOTE_A, note_index)
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
    assert phase_steps == [22, 22, 22, 22]

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

    await spi_write_reg(dut, REG_NOTE_A, ACTIVE_TEST_NOTE)
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
async def test_envelope_generator_modes_and_restart(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not audio_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only audio check because the internal audio hierarchy is not visible")
        return

    await spi_write_reg(dut, REG_CONTROL, 0x01)
    await spi_write_reg(dut, REG_ENVELOPE_PERIOD, 0x01)

    await spi_write_reg(dut, REG_ENVELOPE_CONTROL, 0x08)
    square_levels = []
    for _ in range(32):
        await RisingEdge(dut.clk)
        square_levels.append(envelope_block(dut).envelope_level_o.value.to_unsigned())
    assert set(square_levels) == {0, 7}

    await spi_write_reg(dut, REG_ENVELOPE_CONTROL, 0x09)
    saw_levels = []
    for _ in range(24):
        await RisingEdge(dut.clk)
        saw_levels.append(envelope_block(dut).envelope_level_o.value.to_unsigned())
    assert min(saw_levels) == 0
    assert max(saw_levels) == 7
    assert any(left > right for left, right in zip(saw_levels, saw_levels[1:]))
    assert any((left == 0 and right == 7) for left, right in zip(saw_levels, saw_levels[1:]))

    await spi_write_reg(dut, REG_ENVELOPE_CONTROL, 0x0D)
    await ClockCycles(dut.clk, 2)
    assert envelope_block(dut).envelope_level_o.value.to_unsigned() == 7


@cocotb.test()
async def test_envelope_period_zero_steps_every_clock(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not audio_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only audio check because the internal audio hierarchy is not visible")
        return

    await spi_write_reg(dut, REG_CONTROL, 0x01)
    await spi_write_reg(dut, REG_ENVELOPE_PERIOD, 0x00)
    await spi_write_reg(dut, REG_ENVELOPE_CONTROL, 0x01)

    levels = []
    for _ in range(12):
        await RisingEdge(dut.clk)
        levels.append(envelope_block(dut).envelope_level_o.value.to_unsigned())

    for left, right in zip(levels, levels[1:]):
        expected_right = 7 if left == 0 else left - 1
        assert right == expected_right


@cocotb.test()
async def test_volume_control_and_mixer_follow_levels(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not audio_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only audio check because the internal audio hierarchy is not visible")
        return

    await spi_write_reg(dut, REG_NOTE_A, ACTIVE_TEST_NOTE)
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


@cocotb.test()
async def test_two_channel_mix_reaches_live_range_limits(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not audio_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only audio check because the internal audio hierarchy is not visible")
        return

    await spi_write_reg(dut, REG_NOTE_A, ACTIVE_TEST_NOTE)
    await spi_write_reg(dut, REG_CHANNEL_A_CONTROL, 0x26)
    await spi_write_reg(dut, REG_NOTE_B, ACTIVE_TEST_NOTE)
    await spi_write_reg(dut, REG_CHANNEL_B_CONTROL, 0x26)
    await spi_write_reg(dut, REG_VOLUME_AB, 0x77)
    await spi_write_reg(dut, REG_CONTROL, 0x01)

    mixed_values = []
    for _ in range(4096):
        await RisingEdge(dut.clk)
        mixed_values.append(mixer_block(dut).mixed_sample_o.value.to_signed())

    assert min(mixed_values) == -256
    assert max(mixed_values) == 254


@cocotb.test()
async def test_dac_and_audio_output_drive_activity(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    if not audio_hierarchy_is_visible(dut):
        dut._log.info("Skipping RTL only audio check because the internal audio hierarchy is not visible")
        return

    await spi_write_reg(dut, REG_NOTE_A, ACTIVE_TEST_NOTE)
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
    await ClockCycles(dut.clk, HARD_MUTE_SYNC_CYCLES + 2)
    assert audio_value(dut) == 0

    await set_ui_value(dut, 0x00)
    await spi_write_reg(dut, REG_CONTROL, 0x00)
    await ClockCycles(dut.clk, 4)
    assert audio_value(dut) == 0
    assert int(dac_block(dut).audio_o.value) == 0
    assert dac_block(dut).error_reg.value.to_signed() == 0

    await spi_write_reg(dut, REG_CONTROL, 0x01)
    resumed_audio = await sample_signal_for_cycles(dut, lambda: audio_value(dut), 64)
    assert len(set(resumed_audio)) > 1

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
    await spi_write_reg(dut, REG_NOTE_B, ACTIVE_TEST_NOTE)
    await spi_write_reg(dut, REG_CHANNEL_B_CONTROL, 0x34)
    await spi_write_reg(dut, REG_VOLUME_AB, 0x70)
    await spi_write_reg(dut, REG_ENVELOPE_PERIOD, 0x20)
    await spi_write_reg(dut, REG_ENVELOPE_CONTROL, 0x15)

    assert reg_file(dut).envelope_control_reg.value.to_unsigned() == 0x05
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
    muted_audio = await sample_signal_for_cycles(dut, lambda: audio_value(dut), 16)
    assert set(muted_audio) == {0}

    await set_ui_value(dut, 0x00)
    resumed_audio = await sample_signal_for_cycles(dut, lambda: audio_value(dut), 128)
    assert len(set(resumed_audio)) > 1
