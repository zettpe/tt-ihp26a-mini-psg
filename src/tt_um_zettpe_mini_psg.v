// SPDX-License-Identifier: Apache-2.0
/*
 * Project     : Tiny Tapeout IHP26a Mini PSG
 * File        : tt_um_zettpe_mini_psg.v
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

  wire spi_cs_ni = uio_in[UIO_SPI_CS_N_BIT];
  wire spi_mosi_i = uio_in[UIO_SPI_MOSI_BIT];
  wire spi_sck_i = uio_in[UIO_SPI_SCK_BIT];
  wire spi_miso_o;
  wire spi_miso_oe_o;
  wire audio_o;
  wire channel_a_debug_o;
  wire channel_b_debug_o;
  wire noise_debug_o;
  wire envelope_debug_o;
  wire saturation_flag_o;
  wire spi_access_pulse_o;
  wire spi_read_active_o;

  mini_psg_top mini_psg_top_u (
    .clk_i             (clk),
    .rst_ni            (rst_n),
    .spi_cs_ni         (spi_cs_ni),
    .spi_sck_i         (spi_sck_i),
    .spi_mosi_i        (spi_mosi_i),
    .hard_mute_i       (ui_in[UI_HARD_MUTE_BIT]),
    .spi_miso_o        (spi_miso_o),
    .spi_miso_oe_o     (spi_miso_oe_o),
    .audio_o           (audio_o),
    .channel_a_debug_o (channel_a_debug_o),
    .channel_b_debug_o (channel_b_debug_o),
    .noise_debug_o     (noise_debug_o),
    .envelope_debug_o  (envelope_debug_o),
    .saturation_flag_o (saturation_flag_o),
    .spi_access_pulse_o(spi_access_pulse_o),
    .spi_read_active_o (spi_read_active_o)
  );

  assign uo_out = {
    audio_o,
    channel_a_debug_o,
    channel_b_debug_o,
    noise_debug_o,
    envelope_debug_o,
    spi_access_pulse_o,
    spi_read_active_o,
    saturation_flag_o
  };

  assign uio_out = {5'b00000, spi_miso_o, 2'b00};
  assign uio_oe = {5'b00000, spi_miso_oe_o, 2'b00};

  wire unused_signals = &{
    ena,
    ui_in[7:1],
    uio_in[7:4],
    uio_in[UIO_SPI_MISO_BIT],
    1'b0
  };

endmodule

`default_nettype wire
