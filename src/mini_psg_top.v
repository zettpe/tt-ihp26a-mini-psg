// SPDX-License-Identifier: Apache-2.0
/*
 * File        : mini_psg_top.v
 * Author      : Peter Szentkuti
 * Description : Project top
 */

`default_nettype none
`timescale 1ns / 1ps

module mini_psg_top (
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

  // Keep the internal boundary on simple SPI signals
  mini_psg_control_top mini_psg_control_top_u (
    .clk_i             (clk_i),
    .rst_ni            (rst_ni),
    .spi_cs_ni         (spi_cs_ni),
    .spi_sck_i         (spi_sck_i),
    .spi_mosi_i        (spi_mosi_i),
    .spi_miso_o        (spi_miso_o),
    .spi_miso_oe_o     (spi_miso_oe_o),
    .spi_access_pulse_o(spi_access_pulse_o),
    .spi_read_active_o (spi_read_active_o)
  );

endmodule // mini_psg_top

`default_nettype wire
