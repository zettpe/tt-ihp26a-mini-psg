// SPDX-License-Identifier: Apache-2.0
/*
 * File        : mini_psg_control_top.v
 * Author      : Peter Szentkuti
 * Description : SPI register block
 *
 * Connects the SPI slave to the register file, sends the selected
 * register byte on MISO and sends the stored values to the audio block
 */

`default_nettype none
`timescale 1ns / 1ps

// Connects the SPI slave and the register file
module mini_psg_control_top (
  input  wire       clk_i,
  input  wire       rst_ni,
  input  wire       spi_cs_ni,
  input  wire       spi_sck_i,
  input  wire       spi_mosi_i,
  output wire       spi_miso_o,
  output wire       spi_miso_oe_o,
  output wire       spi_access_pulse_o,
  output wire       spi_read_active_o,
  output wire       clear_enable_o,
  output wire       audio_enable_o,
  output wire [7:0] note_a_value_o,
  output wire [7:0] channel_a_control_value_o,
  output wire [7:0] note_b_value_o,
  output wire [7:0] channel_b_control_value_o,
  output wire [7:0] volume_ab_value_o,
  output wire [7:0] noise_control_value_o,
  output wire [7:0] envelope_control_value_o,
  output wire [7:0] envelope_period_value_o,
  output wire       envelope_restart_pulse_o
);

  localparam [3:0] ADDR_CONTROL = 4'h0;
  localparam [3:0] ADDR_ENVELOPE_CONTROL = 4'h7;

  localparam integer CONTROL_AUDIO_ENABLE_BIT = 0;
  localparam integer CONTROL_CLEAR_BIT = 1;
  localparam integer ENVELOPE_RESTART_BIT = 2;

  wire [3:0] spi_write_address;
  wire [7:0] spi_write_data;
  wire       spi_write_enable;
  wire [3:0] spi_read_address;
  wire       spi_miso_data;
  wire       spi_miso_output_enable;
  wire [7:0] spi_read_data;
  wire [7:0] control_value;
  wire       spi_miso_output_enable_safe;

  // Release the shared MISO line as soon as CS_N goes high
  assign spi_miso_o = spi_miso_data;
  assign spi_miso_output_enable_safe = spi_miso_output_enable & ~spi_cs_ni;
  assign spi_miso_oe_o = spi_miso_output_enable_safe;

  // Build the clear and envelope restart pulses from accepted writes
  assign clear_enable_o = spi_write_enable &&
      (spi_write_address == ADDR_CONTROL) &&
      spi_write_data[CONTROL_CLEAR_BIT];
  assign audio_enable_o = control_value[CONTROL_AUDIO_ENABLE_BIT];
  assign envelope_restart_pulse_o = spi_write_enable &&
      (spi_write_address == ADDR_ENVELOPE_CONTROL) &&
      spi_write_data[ENVELOPE_RESTART_BIT];

  spi_slave spi_slave_u (
    .clk_i                (clk_i),
    .rst_ni               (rst_ni),
    .spi_cs_ni            (spi_cs_ni),
    .spi_sck_i            (spi_sck_i),
    .spi_mosi_i           (spi_mosi_i),
    .read_data_i          (spi_read_data),
    .write_address_o      (spi_write_address),
    .write_data_o         (spi_write_data),
    .write_enable_o       (spi_write_enable),
    .read_address_o       (spi_read_address),
    .read_active_o        (spi_read_active_o),
    .access_pulse_o       (spi_access_pulse_o),
    .miso_data_o          (spi_miso_data),
    .miso_output_enable_o (spi_miso_output_enable)
  );

  register_file register_file_u (
    .clk_i                    (clk_i),
    .rst_ni                   (rst_ni),
    .write_enable_i           (spi_write_enable),
    .write_address_i          (spi_write_address),
    .write_data_i             (spi_write_data),
    .read_address_i           (spi_read_address),
    .read_data_o              (spi_read_data),
    .control_value_o          (control_value),
    .note_a_value_o           (note_a_value_o),
    .channel_a_control_value_o(channel_a_control_value_o),
    .note_b_value_o           (note_b_value_o),
    .channel_b_control_value_o(channel_b_control_value_o),
    .volume_ab_value_o        (volume_ab_value_o),
    .noise_control_value_o    (noise_control_value_o),
    .envelope_control_value_o (envelope_control_value_o),
    .envelope_period_value_o  (envelope_period_value_o)
  );

endmodule // mini_psg_control_top

`default_nettype wire
