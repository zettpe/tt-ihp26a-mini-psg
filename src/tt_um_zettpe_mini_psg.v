// SPDX-License-Identifier: Apache-2.0
/*
 * File        : register_file.v
 * Project     : Tiny Tapeout IHP26a Mini PSG
 * Author      : Peter Szentkuti
 * Description : See documentation
 */

`default_nettype none
`timescale 1ns / 1ps

// Tiny Tapeout wrapper
module tt_um_zettpe_mini_psg (
  input  wire [7:0] ui_in,
  output wire [7:0] uo_out,
  input  wire [7:0] uio_in,
  output wire [7:0] uio_out,
  output wire [7:0] uio_oe,
  input  wire       ena,
  input  wire       clk,
  input  wire       rst_n
);

  localparam integer UIO_SPI_CS_N_BIT = 0;
  localparam integer UIO_SPI_MOSI_BIT = 1;
  localparam integer UIO_SPI_MISO_BIT = 2;
  localparam integer UIO_SPI_SCK_BIT = 3;

  wire       spi_cs_ni = uio_in[UIO_SPI_CS_N_BIT];
  wire       spi_mosi_i = uio_in[UIO_SPI_MOSI_BIT];
  wire       spi_sck_i = uio_in[UIO_SPI_SCK_BIT];
  wire       spi_miso_o;
  wire       spi_miso_oe_o;
  wire       spi_access_pulse;
  wire       spi_read_active;

  mini_psg_top mini_psg_top_u (
    .clk_i             (clk),
    .rst_ni            (rst_n),
    .spi_cs_ni         (spi_cs_ni),
    .spi_sck_i         (spi_sck_i),
    .spi_mosi_i        (spi_mosi_i),
    .spi_miso_o        (spi_miso_o),
    .spi_miso_oe_o     (spi_miso_oe_o),
    .spi_access_pulse_o(spi_access_pulse),
    .spi_read_active_o (spi_read_active)
  );

  assign uo_out = {
    5'b00000,
    spi_access_pulse,
    spi_read_active,
    1'b0
  };

  assign uio_out = {5'b00000, spi_miso_o, 2'b00};
  assign uio_oe = {5'b00000, spi_miso_oe_o, 2'b00};

  wire unused_signals = &{
    ena,
    ui_in,
    uio_in[7:4],
    uio_in[UIO_SPI_MISO_BIT],
    1'b0
  };

endmodule

`default_nettype wire
