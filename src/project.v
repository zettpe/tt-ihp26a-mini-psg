/*
 * Copyright (c) 2026 Peter Szentkuti
 * SPDX-License-Identifier: Apache-2.0
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

  // All output pins must be assigned. If not used, assign to 0.
  assign uo_out  = ui_in + uio_in;
  assign uio_out = 8'h00;
  assign uio_oe  = 8'h00;

  // List all unused inputs to prevent warnings.
  wire _unused = &{ena, clk, rst_n, 1'b0};

endmodule
