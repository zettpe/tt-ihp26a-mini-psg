// SPDX-License-Identifier: Apache-2.0
/*
 * Project : Tiny Tapeout IHP26a Mini PSG
 * File    : tt_um_zettpe_mini_psg.v
 * Author  : Peter Szentkuti
 *
 * Tiny Tapeout wrapper
 *
 * Maps the board level pins to the internal project core. Exposes hard
 * mute, write only SPI control and 1 bit audio output.
 */

`default_nettype none

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

  // Tiny Tapeout pin map for this wrapper
  localparam integer UI_HARD_MUTE_BIT = 0;

  localparam integer UIO_SPI_CS_N_BIT = 0;
  localparam integer UIO_SPI_MOSI_BIT = 1;
  localparam integer UIO_SPI_SCK_BIT = 2;

  // Decode the SPI and audio pins from the wrapper ports
  wire spi_cs_ni = uio_in[UIO_SPI_CS_N_BIT];
  wire spi_mosi_i = uio_in[UIO_SPI_MOSI_BIT];
  wire spi_sck_i = uio_in[UIO_SPI_SCK_BIT];
  wire audio_o;

  mini_psg_top mini_psg_top_u (
    .clk_i      (clk),
    .rst_ni     (rst_n),
    .spi_cs_ni  (spi_cs_ni),
    .spi_sck_i  (spi_sck_i),
    .spi_mosi_i (spi_mosi_i),
    .hard_mute_i(ui_in[UI_HARD_MUTE_BIT]),
    .audio_o    (audio_o)
  );

  // Drive only uo_out[7] and keep all bidirectional pins released
  assign uo_out = {audio_o, 7'b0000000};
  assign uio_out = 8'b00000000;
  assign uio_oe = 8'b00000000;

  // Fold unused wrapper inputs away to keep lint quiet
  wire unused_signals = &{
    ena,
    ui_in[7:1],
    uio_in[7:4],
    uio_in[3],
    1'b0
  };

endmodule
