// SPDX-License-Identifier: Apache-2.0
/*
 * File        : mini_psg_control_top.v
 * Author      : Peter Szentkuti
 * Description : Top block for SPI register access
 *
 * Connects the SPI slave to the register file and sends the selected read
 * byte back to MISO. The MISO output enable is also gated with the external
 * CS_N pin so the shared line is released as soon as a transfer ends
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
  output wire       spi_read_active_o
);
  wire [3:0] spi_write_address;
  wire [7:0] spi_write_data;
  wire       spi_write_enable;
  wire [3:0] spi_read_address;
  wire       spi_miso_data;
  wire       spi_miso_output_enable;
  wire [7:0] spi_read_data;
  wire       spi_miso_output_enable_safe;

  // Release the shared MISO line as soon as CS_N goes high
  assign spi_miso_o = spi_miso_data;
  assign spi_miso_output_enable_safe = spi_miso_output_enable & ~spi_cs_ni;
  assign spi_miso_oe_o = spi_miso_output_enable_safe;

  spi_slave spi_slave_u (
    .clk_i              (clk_i),
    .rst_ni             (rst_ni),
    .spi_cs_ni          (spi_cs_ni),
    .spi_sck_i          (spi_sck_i),
    .spi_mosi_i         (spi_mosi_i),
    .read_data_i        (spi_read_data),
    .write_address_o    (spi_write_address),
    .write_data_o       (spi_write_data),
    .write_enable_o     (spi_write_enable),
    .read_address_o     (spi_read_address),
    .read_active_o      (spi_read_active_o),
    .access_pulse_o     (spi_access_pulse_o),
    .miso_data_o        (spi_miso_data),
    .miso_output_enable_o(spi_miso_output_enable)
  );

  register_file register_file_u (
    .clk_i          (clk_i),
    .rst_ni         (rst_ni),
    .write_enable_i (spi_write_enable),
    .write_address_i(spi_write_address),
    .write_data_i   (spi_write_data),
    .read_address_i (spi_read_address),
    .read_data_o    (spi_read_data)
  );

endmodule // mini_psg_control_top

`default_nettype wire
