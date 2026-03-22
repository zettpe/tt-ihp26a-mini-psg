`default_nettype none
`timescale 1ns / 1ps

// Small top wrapper for SPI checks
module tb;

  reg        clk = 1'b0;
  reg        rst_n = 1'b0;
  reg        ena = 1'b0;
  reg  [7:0] ui_in = 8'h00;
  reg  [7:0] uio_in = 8'h01;
  wire [7:0] uo_out;
  wire [7:0] uio_out;
  wire [7:0] uio_oe;

  initial begin : init_dump
    $dumpfile("tb.fst");
    $dumpvars(0, tb);
    #1;
  end

  tt_um_zettpe_mini_psg user_project_u (
    .ui_in   (ui_in),
    .uo_out  (uo_out),
    .uio_in  (uio_in),
    .uio_out (uio_out),
    .uio_oe  (uio_oe),
    .ena     (ena),
    .clk     (clk),
    .rst_n   (rst_n)
  );

  wire unused_signals = &{uo_out, uio_out, uio_oe, 1'b0};

endmodule

`default_nettype wire
