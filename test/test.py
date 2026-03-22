# SPDX-FileCopyrightText: © 2026 Peter Szentkuti
# SPDX-License-Identifier: Apache-2.0

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, ReadOnly, Timer


CLK_PERIOD_NS = 40
SPI_MIN_HALF_PERIOD_CYCLES = 4
SPI_MIN_HALF_PERIOD_NS = CLK_PERIOD_NS * SPI_MIN_HALF_PERIOD_CYCLES
SPI_MIN_FRAME_GAP_NS = SPI_MIN_HALF_PERIOD_NS

SPI_CS_BIT = 0
SPI_MOSI_BIT = 1
SPI_MISO_BIT = 2
SPI_SCK_BIT = 3

REG_CONTROL = 0x0
REG_NOTE_A = 0x1
REG_CHANNEL_A_CONTROL = 0x2
REG_NOTE_B = 0x3
REG_CHANNEL_B_CONTROL = 0x4
REG_VOLUME_AB = 0x5
REG_NOISE_CONTROL = 0x6
REG_ENVELOPE_CONTROL = 0x7
REG_ENVELOPE_PERIOD = 0x8
REG_STATUS = 0x9
REG_ID = 0xA
UNMAPPED_ADDRESS = 0xF

ALL_REG_ADDRESSES = tuple(range(REG_ID + 1))


def set_spi_lines(dut, cs_n=1, sck=0, mosi=0):
    value = 0
    value |= (cs_n & 1) << SPI_CS_BIT
    value |= (mosi & 1) << SPI_MOSI_BIT
    value |= (sck & 1) << SPI_SCK_BIT
    dut.uio_in.value = value


def miso_value(dut):
    return (dut.uio_out.value.to_unsigned() >> SPI_MISO_BIT) & 1


def miso_oe(dut):
    return (dut.uio_oe.value.to_unsigned() >> SPI_MISO_BIT) & 1


def read_phase_value(dut):
    return (dut.uo_out.value.to_unsigned() >> 1) & 1


def ctrl_top(dut):
    return dut.user_project_u.mini_psg_top_u.mini_psg_control_top_u


def reg_file(dut):
    return ctrl_top(dut).register_file_u


def byte_to_bits(value):
    return [((value >> bit_index) & 1) for bit_index in range(7, -1, -1)]


def bits_to_byte(bit_values):
    value = 0
    for bit_value in bit_values:
        value = (value << 1) | bit_value
    return value


def new_phase_flags():
    return {
        "miso_oe_seen": False,
        "read_phase_seen": False,
    }


def sample_phase_flags(dut, phase_flags):
    phase_flags["miso_oe_seen"] |= bool(miso_oe(dut))
    phase_flags["read_phase_seen"] |= bool(read_phase_value(dut))


def new_reg_model():
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
        "write_seen": 0,
    }


def model_write(model, address, data):
    model["write_seen"] = 1

    if address == REG_CONTROL:
        model[REG_CONTROL] = ((data & 0x04) | (data & 0x01))

        if data & 0x02:
            model.update(new_reg_model())
    elif address == REG_NOTE_A:
        model[REG_NOTE_A] = data & 0xFF
    elif address == REG_CHANNEL_A_CONTROL:
        model[REG_CHANNEL_A_CONTROL] = data & 0xFF
    elif address == REG_NOTE_B:
        model[REG_NOTE_B] = data & 0xFF
    elif address == REG_CHANNEL_B_CONTROL:
        model[REG_CHANNEL_B_CONTROL] = data & 0xFF
    elif address == REG_VOLUME_AB:
        model[REG_VOLUME_AB] = data & 0xFF
    elif address == REG_NOISE_CONTROL:
        model[REG_NOISE_CONTROL] = data & 0xFF
    elif address == REG_ENVELOPE_CONTROL:
        model[REG_ENVELOPE_CONTROL] = data & 0x1B
    elif address == REG_ENVELOPE_PERIOD:
        model[REG_ENVELOPE_PERIOD] = data & 0xFF


def model_read(model, address):
    if address == REG_STATUS:
        return 0x04 if model["write_seen"] else 0x00

    if address == REG_ID:
        return 0xDF

    return model.get(address, 0x00)


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


async def spi_shift_bits_timed(dut, bit_values, cs_n, half_period_ns):
    sampled_bits = []
    phase_flags = new_phase_flags()

    for bit_value in bit_values:
        set_spi_lines(dut, cs_n=cs_n, sck=0, mosi=bit_value)
        await Timer(half_period_ns, unit="ns")

        set_spi_lines(dut, cs_n=cs_n, sck=1, mosi=bit_value)
        await ReadOnly()
        sample_phase_flags(dut, phase_flags)
        sampled_bits.append(miso_value(dut))
        await Timer(half_period_ns, unit="ns")

        set_spi_lines(dut, cs_n=cs_n, sck=0, mosi=bit_value)
        await Timer(half_period_ns, unit="ns")

    return sampled_bits, phase_flags


async def spi_transfer_byte_timed(dut, value, half_period_ns):
    sampled_bits, phase_flags = await spi_shift_bits_timed(
        dut,
        byte_to_bits(value),
        cs_n=0,
        half_period_ns=half_period_ns,
    )

    return {
        "response": bits_to_byte(sampled_bits),
        "miso_oe_seen": phase_flags["miso_oe_seen"],
        "read_phase_seen": phase_flags["read_phase_seen"],
    }


async def spi_begin_frame(dut, setup_ns=SPI_MIN_HALF_PERIOD_NS):
    set_spi_lines(dut, cs_n=0, sck=0, mosi=0)
    await ReadOnly()
    await Timer(setup_ns, unit="ns")


async def spi_end_frame(dut, idle_ns=SPI_MIN_FRAME_GAP_NS):
    set_spi_lines(dut, cs_n=1, sck=0, mosi=0)
    await ReadOnly()

    frame_flags = {
        "miso_oe_after_cs": bool(miso_oe(dut)),
        "read_phase_after_cs": bool(read_phase_value(dut)),
    }

    await Timer(idle_ns, unit="ns")
    return frame_flags


async def spi_raw_frame_timed(
    dut,
    byte_values,
    half_period_ns=SPI_MIN_HALF_PERIOD_NS,
    setup_ns=SPI_MIN_HALF_PERIOD_NS,
    idle_ns=SPI_MIN_FRAME_GAP_NS,
):
    await spi_begin_frame(dut, setup_ns=setup_ns)

    byte_results = []
    for value in byte_values:
        byte_results.append(
            await spi_transfer_byte_timed(
                dut,
                value,
                half_period_ns=half_period_ns,
            )
        )

    frame_flags = await spi_end_frame(dut, idle_ns=idle_ns)
    return byte_results, frame_flags


async def spi_raw_transaction_timed(
    dut,
    command_byte,
    data_byte,
    half_period_ns=SPI_MIN_HALF_PERIOD_NS,
):
    byte_results, frame_flags = await spi_raw_frame_timed(
        dut,
        [command_byte, data_byte],
        half_period_ns=half_period_ns,
    )
    return byte_results[0], byte_results[1], frame_flags


async def spi_write_reg(dut, address, data, half_period_ns=SPI_MIN_HALF_PERIOD_NS):
    return await spi_raw_transaction_timed(
        dut,
        address & 0x0F,
        data & 0xFF,
        half_period_ns=half_period_ns,
    )


async def spi_read_reg(dut, address, half_period_ns=SPI_MIN_HALF_PERIOD_NS):
    return await spi_raw_transaction_timed(
        dut,
        0x80 | (address & 0x0F),
        0x00,
        half_period_ns=half_period_ns,
    )


async def drive_idle_bus_activity(
    dut,
    byte_values,
    half_period_ns=SPI_MIN_HALF_PERIOD_NS,
):
    phase_flags = new_phase_flags()

    for value in byte_values:
        _, bit_flags = await spi_shift_bits_timed(
            dut,
            byte_to_bits(value),
            cs_n=1,
            half_period_ns=half_period_ns,
        )
        phase_flags["miso_oe_seen"] |= bit_flags["miso_oe_seen"]
        phase_flags["read_phase_seen"] |= bit_flags["read_phase_seen"]

    return phase_flags


@cocotb.test()
async def test_reset_defaults_and_spi_readback(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    assert dut.uo_out.value.to_unsigned() == 0
    assert dut.uio_oe.value.to_unsigned() == 0
    assert reg_file(dut).note_a_reg.value.to_unsigned() == 0x0F
    assert reg_file(dut).note_b_reg.value.to_unsigned() == 0x0F
    assert reg_file(dut).envelope_period_reg.value.to_unsigned() == 0x10

    expected_defaults = {
        REG_CONTROL: 0x00,
        REG_NOTE_A: 0x0F,
        REG_CHANNEL_A_CONTROL: 0x00,
        REG_NOTE_B: 0x0F,
        REG_CHANNEL_B_CONTROL: 0x00,
        REG_VOLUME_AB: 0x00,
        REG_NOISE_CONTROL: 0x00,
        REG_ENVELOPE_CONTROL: 0x00,
        REG_ENVELOPE_PERIOD: 0x10,
        REG_STATUS: 0x00,
        REG_ID: 0xDF,
    }

    for address, expected_value in expected_defaults.items():
        command_result, data_result, frame_flags = await spi_read_reg(dut, address)

        assert command_result["response"] == 0x00
        assert data_result["response"] == expected_value
        assert not command_result["miso_oe_seen"]
        assert not command_result["read_phase_seen"]
        assert data_result["miso_oe_seen"]
        assert data_result["read_phase_seen"]
        assert not frame_flags["miso_oe_after_cs"]


@cocotb.test()
async def test_spi_write_readback_and_invalid_commands(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

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
        command_result, data_result, frame_flags = await spi_write_reg(dut, address, value)
        assert command_result["response"] == 0x00
        assert data_result["response"] == 0x00
        assert not command_result["miso_oe_seen"]
        assert not data_result["miso_oe_seen"]
        assert not command_result["read_phase_seen"]
        assert not data_result["read_phase_seen"]
        assert not frame_flags["miso_oe_after_cs"]

    await spi_write_reg(dut, UNMAPPED_ADDRESS, 0x55)

    for address, expected_value in (
        (REG_CONTROL, 0x05),
        (REG_NOTE_A, 0x10),
        (REG_CHANNEL_A_CONTROL, 0x24),
        (REG_NOTE_B, 0x33),
        (REG_CHANNEL_B_CONTROL, 0x2C),
        (REG_VOLUME_AB, 0x93),
        (REG_NOISE_CONTROL, 0x07),
        (REG_ENVELOPE_CONTROL, 0x1B),
        (REG_ENVELOPE_PERIOD, 0x08),
    ):
        command_result, data_result, frame_flags = await spi_read_reg(dut, address)
        assert command_result["response"] == 0x00
        assert data_result["response"] == expected_value
        assert not command_result["miso_oe_seen"]
        assert data_result["miso_oe_seen"]
        assert not frame_flags["miso_oe_after_cs"]

    _, status_result, _ = await spi_read_reg(dut, REG_STATUS)
    assert status_result["response"] == 0x04
    assert int(reg_file(dut).write_seen_reg.value) == 1

    _, unmapped_result, _ = await spi_read_reg(dut, UNMAPPED_ADDRESS)
    assert unmapped_result["response"] == 0x00

    command_result, data_result, frame_flags = await spi_raw_transaction_timed(
        dut,
        0x10,
        0xAA,
    )
    assert command_result["response"] == 0x00
    assert data_result["response"] == 0x00
    assert not command_result["miso_oe_seen"]
    assert not data_result["miso_oe_seen"]
    assert not command_result["read_phase_seen"]
    assert not data_result["read_phase_seen"]
    assert not frame_flags["miso_oe_after_cs"]

    _, control_result, _ = await spi_read_reg(dut, REG_CONTROL)
    assert control_result["response"] == 0x05

    command_result, data_result, frame_flags = await spi_raw_transaction_timed(
        dut,
        0x90,
        0x00,
    )
    assert command_result["response"] == 0x00
    assert data_result["response"] == 0x00
    assert not command_result["miso_oe_seen"]
    assert not data_result["miso_oe_seen"]
    assert not command_result["read_phase_seen"]
    assert not data_result["read_phase_seen"]
    assert not frame_flags["miso_oe_after_cs"]


@cocotb.test()
async def test_soft_reset_clears_written_registers(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    await spi_write_reg(dut, REG_CONTROL, 0x05)
    await spi_write_reg(dut, REG_NOTE_A, 0x7B)
    await spi_write_reg(dut, REG_CHANNEL_A_CONTROL, 0x2C)
    await spi_write_reg(dut, REG_NOTE_B, 0x7B)
    await spi_write_reg(dut, REG_CHANNEL_B_CONTROL, 0x2C)
    await spi_write_reg(dut, REG_VOLUME_AB, 0xFF)
    await spi_write_reg(dut, REG_NOISE_CONTROL, 0x03)
    await spi_write_reg(dut, REG_ENVELOPE_CONTROL, 0x0D)
    await spi_write_reg(dut, REG_ENVELOPE_PERIOD, 0x02)

    assert int(reg_file(dut).write_seen_reg.value) == 1

    await spi_write_reg(dut, REG_CONTROL, 0x03)
    await ClockCycles(dut.clk, 4)

    for address, expected_value in (
        (REG_CONTROL, 0x00),
        (REG_NOTE_A, 0x0F),
        (REG_CHANNEL_A_CONTROL, 0x00),
        (REG_NOTE_B, 0x0F),
        (REG_CHANNEL_B_CONTROL, 0x00),
        (REG_VOLUME_AB, 0x00),
        (REG_NOISE_CONTROL, 0x00),
        (REG_ENVELOPE_CONTROL, 0x00),
        (REG_ENVELOPE_PERIOD, 0x10),
        (REG_STATUS, 0x00),
    ):
        _, data_result, _ = await spi_read_reg(dut, address)
        assert data_result["response"] == expected_value

    assert dut.uo_out.value.to_unsigned() == 0


@cocotb.test()
async def test_spi_single_frame_ignores_extra_bytes(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    byte_results, frame_flags = await spi_raw_frame_timed(
        dut,
        [REG_NOTE_A, 0x22, 0x44],
    )
    assert [result["response"] for result in byte_results] == [0, 0, 0]
    assert [result["miso_oe_seen"] for result in byte_results] == [False, False, False]
    assert [result["read_phase_seen"] for result in byte_results] == [False, False, False]
    assert not frame_flags["miso_oe_after_cs"]

    _, note_result, _ = await spi_read_reg(dut, REG_NOTE_A)
    assert note_result["response"] == 0x22

    byte_results, frame_flags = await spi_raw_frame_timed(
        dut,
        [0x80 | REG_NOTE_A, 0x00, 0x00],
    )
    assert [result["response"] for result in byte_results] == [0, 0x22, 0]
    assert [result["miso_oe_seen"] for result in byte_results] == [False, True, False]
    assert [result["read_phase_seen"] for result in byte_results] == [False, True, False]
    assert not frame_flags["miso_oe_after_cs"]


@cocotb.test()
async def test_valid_read_drives_miso_only_in_data_byte(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    await spi_write_reg(dut, REG_NOTE_A, 0x33)

    command_result, data_result, frame_flags = await spi_read_reg(
        dut,
        REG_NOTE_A,
        half_period_ns=SPI_MIN_HALF_PERIOD_NS,
    )
    assert command_result["response"] == 0x00
    assert data_result["response"] == 0x33
    assert not command_result["miso_oe_seen"]
    assert data_result["miso_oe_seen"]
    assert not command_result["read_phase_seen"]
    assert data_result["read_phase_seen"]
    assert not frame_flags["miso_oe_after_cs"]

    command_result, data_result, frame_flags = await spi_raw_transaction_timed(
        dut,
        0x90,
        0x00,
        half_period_ns=SPI_MIN_HALF_PERIOD_NS,
    )
    assert command_result["response"] == 0x00
    assert data_result["response"] == 0x00
    assert not command_result["miso_oe_seen"]
    assert not data_result["miso_oe_seen"]
    assert not command_result["read_phase_seen"]
    assert not data_result["read_phase_seen"]
    assert not frame_flags["miso_oe_after_cs"]


@cocotb.test()
async def test_miso_is_released_immediately_on_cs_high(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    await spi_write_reg(dut, REG_NOTE_A, 0x66)

    await spi_begin_frame(dut)
    await spi_transfer_byte_timed(dut, 0x80 | REG_NOTE_A, SPI_MIN_HALF_PERIOD_NS)
    _, phase_flags = await spi_shift_bits_timed(
        dut,
        byte_to_bits(0x00)[:3],
        cs_n=0,
        half_period_ns=SPI_MIN_HALF_PERIOD_NS,
    )

    assert phase_flags["miso_oe_seen"]
    assert phase_flags["read_phase_seen"]
    assert miso_oe(dut) == 1

    set_spi_lines(dut, cs_n=1, sck=0, mosi=0)
    await ReadOnly()
    assert miso_oe(dut) == 0

    await Timer(SPI_MIN_FRAME_GAP_NS, unit="ns")
    _, note_result, _ = await spi_read_reg(dut, REG_NOTE_A)
    assert note_result["response"] == 0x66


@cocotb.test()
async def test_min_timing_with_phase_sweep(dut):
    await start_test_clock(dut)

    for phase_offset_ns, value in zip((0, 5, 11, 19, 27, 35), (0x21, 0x32, 0x43, 0x54, 0x65, 0x76)):
        await apply_reset(dut)
        await wait_ns_if_needed(phase_offset_ns)

        await spi_write_reg(
            dut,
            REG_NOTE_A,
            value,
            half_period_ns=SPI_MIN_HALF_PERIOD_NS,
        )
        _, read_result, frame_flags = await spi_read_reg(
            dut,
            REG_NOTE_A,
            half_period_ns=SPI_MIN_HALF_PERIOD_NS,
        )

        assert read_result["response"] == value
        assert not frame_flags["miso_oe_after_cs"]


@cocotb.test()
async def test_cs_abort_mid_command_is_ignored(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    await spi_begin_frame(dut)
    _, phase_flags = await spi_shift_bits_timed(
        dut,
        byte_to_bits(REG_NOTE_A)[:4],
        cs_n=0,
        half_period_ns=SPI_MIN_HALF_PERIOD_NS,
    )
    assert not phase_flags["miso_oe_seen"]

    set_spi_lines(dut, cs_n=1, sck=0, mosi=0)
    await ReadOnly()
    assert miso_oe(dut) == 0
    await Timer(SPI_MIN_FRAME_GAP_NS, unit="ns")

    _, status_result, _ = await spi_read_reg(dut, REG_STATUS)
    _, note_result, _ = await spi_read_reg(dut, REG_NOTE_A)
    assert status_result["response"] == 0x00
    assert note_result["response"] == 0x0F

    await spi_write_reg(dut, REG_NOTE_A, 0x2A)
    _, note_result, _ = await spi_read_reg(dut, REG_NOTE_A)
    assert note_result["response"] == 0x2A


@cocotb.test()
async def test_cs_abort_mid_data_is_ignored(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    await spi_begin_frame(dut)
    await spi_transfer_byte_timed(dut, REG_NOTE_A, SPI_MIN_HALF_PERIOD_NS)
    _, phase_flags = await spi_shift_bits_timed(
        dut,
        byte_to_bits(0xA0)[:4],
        cs_n=0,
        half_period_ns=SPI_MIN_HALF_PERIOD_NS,
    )
    assert not phase_flags["miso_oe_seen"]

    set_spi_lines(dut, cs_n=1, sck=0, mosi=0)
    await ReadOnly()
    assert miso_oe(dut) == 0
    await Timer(SPI_MIN_FRAME_GAP_NS, unit="ns")

    _, status_result, _ = await spi_read_reg(dut, REG_STATUS)
    _, note_result, _ = await spi_read_reg(dut, REG_NOTE_A)
    assert status_result["response"] == 0x00
    assert note_result["response"] == 0x0F

    await spi_write_reg(dut, REG_NOTE_A, 0x7C)
    _, note_result, _ = await spi_read_reg(dut, REG_NOTE_A)
    assert note_result["response"] == 0x7C


@cocotb.test()
async def test_spi_ignores_activity_while_cs_high(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    phase_flags = await drive_idle_bus_activity(
        dut,
        [0xAA, 0x55, 0xF0],
        half_period_ns=SPI_MIN_HALF_PERIOD_NS,
    )
    assert not phase_flags["miso_oe_seen"]
    assert not phase_flags["read_phase_seen"]

    _, status_result, _ = await spi_read_reg(dut, REG_STATUS)
    _, control_result, _ = await spi_read_reg(dut, REG_CONTROL)
    assert status_result["response"] == 0x00
    assert control_result["response"] == 0x00


@cocotb.test()
async def test_random_legal_spi_traffic_matches_register_model(dut):
    await start_test_clock(dut)
    await apply_reset(dut)

    rng = random.Random(20260322)
    reg_model = new_reg_model()

    for _ in range(40):
        await wait_ns_if_needed(rng.randrange(0, CLK_PERIOD_NS))
        half_period_ns = SPI_MIN_HALF_PERIOD_NS + rng.randrange(0, 5) * 20

        if rng.randrange(0, 2) == 0:
            address = rng.choice(ALL_REG_ADDRESSES)
            data = rng.randrange(0, 256)
            command_result, data_result, frame_flags = await spi_write_reg(
                dut,
                address,
                data,
                half_period_ns=half_period_ns,
            )

            assert command_result["response"] == 0x00
            assert data_result["response"] == 0x00
            assert not command_result["miso_oe_seen"]
            assert not data_result["miso_oe_seen"]
            assert not command_result["read_phase_seen"]
            assert not data_result["read_phase_seen"]
            assert not frame_flags["miso_oe_after_cs"]

            model_write(reg_model, address, data)
        else:
            address = rng.choice(ALL_REG_ADDRESSES)
            command_result, data_result, frame_flags = await spi_read_reg(
                dut,
                address,
                half_period_ns=half_period_ns,
            )

            assert command_result["response"] == 0x00
            assert data_result["response"] == model_read(reg_model, address)
            assert not command_result["miso_oe_seen"]
            assert command_result["read_phase_seen"] == 0
            assert data_result["miso_oe_seen"]
            assert data_result["read_phase_seen"]
            assert not frame_flags["miso_oe_after_cs"]

    for address in ALL_REG_ADDRESSES:
        _, data_result, _ = await spi_read_reg(dut, address)
        assert data_result["response"] == model_read(reg_model, address)
