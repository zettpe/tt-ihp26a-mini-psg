// SPDX-License-Identifier: Apache-2.0
/*
 * File   : mini_psg_control_top.v
 * Author : Peter Szentkuti
 *
 * Control path wrapper
 *
 * Connects the write only SPI slave and the register file, sends the
 * stored control values to the audio path and generates the CONTROL clear
 * and ENVELOPE restart pulses from writes.
 */

`default_nettype none

module mini_psg_control_top (
  input  wire       clk_i,
  input  wire       rst_ni,
  input  wire       spi_cs_ni,
  input  wire       spi_sck_i,
  input  wire       spi_mosi_i,
  output wire       clear_enable_o,
  output wire       audio_enable_o,
  output wire [6:0] note_a_value_o,
  output wire [4:0] channel_a_control_value_o,
  output wire [6:0] note_b_value_o,
  output wire [4:0] channel_b_control_value_o,
  output wire [5:0] volume_ab_value_o,
  output wire [2:0] envelope_control_value_o,
  output wire [7:0] envelope_period_value_o,
  output wire       envelope_restart_pulse_o
);

  localparam [3:0] ADDR_CONTROL = 4'h0;
  localparam [3:0] ADDR_ENVELOPE_CONTROL = 4'h7;

  localparam integer CONTROL_CLEAR_BIT = 1;
  localparam integer ENVELOPE_RESTART_BIT = 2;

  wire [3:0] spi_write_address;
  wire [7:0] spi_write_data;
  wire       spi_write_enable;
  wire       control_value;

  // Build the clear and envelope restart pulses from accepted writes
  assign clear_enable_o = spi_write_enable &&
      (spi_write_address == ADDR_CONTROL) &&
      spi_write_data[CONTROL_CLEAR_BIT];
  assign audio_enable_o = control_value;
  assign envelope_restart_pulse_o = spi_write_enable &&
      (spi_write_address == ADDR_ENVELOPE_CONTROL) &&
      spi_write_data[ENVELOPE_RESTART_BIT];

  // Sample the SPI pins and decode one write frame at a time
  spi_slave spi_slave_u (
    .clk_i                (clk_i),
    .rst_ni               (rst_ni),
    .spi_cs_ni            (spi_cs_ni),
    .spi_sck_i            (spi_sck_i),
    .spi_mosi_i           (spi_mosi_i),
    .write_address_o      (spi_write_address),
    .write_data_o         (spi_write_data),
    .write_enable_o       (spi_write_enable)
  );

  // Store the live control registers and expose their decoded fields
  register_file register_file_u (
    .clk_i                    (clk_i),
    .rst_ni                   (rst_ni),
    .write_enable_i           (spi_write_enable),
    .write_address_i          (spi_write_address),
    .write_data_i             (spi_write_data),
    .control_value_o          (control_value),
    .note_a_value_o           (note_a_value_o),
    .channel_a_control_value_o(channel_a_control_value_o),
    .note_b_value_o           (note_b_value_o),
    .channel_b_control_value_o(channel_b_control_value_o),
    .volume_ab_value_o        (volume_ab_value_o),
    .envelope_control_value_o (envelope_control_value_o),
    .envelope_period_value_o  (envelope_period_value_o)
  );

endmodule // mini_psg_control_top
