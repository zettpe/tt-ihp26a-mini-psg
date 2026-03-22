// SPDX-License-Identifier: Apache-2.0
/*
 * File        : noise_generator.v
 * Author      : Peter Szentkuti
 * Description : Shared noise generator
 *
 * Generates a shared noise bit and signed noise sample with a small
 * rate divider
 */

`default_nettype none
`timescale 1ns / 1ps

// Generates the shared noise bit and noise sample
module noise_generator (
  input  wire              clk_i,
  input  wire              rst_ni,
  input  wire              clear_enable_i,
  input  wire              noise_enable_i,
  input  wire [2:0]        rate_select_i,
  output wire              noise_bit_o,
  output wire signed [7:0] noise_sample_o
);

  localparam signed [7:0] NOISE_AMPLITUDE = 8'sd48;

  reg  [14:0] lfsr_reg;
  reg  [7:0]  divider_reg;
  // Keep the divider from reaching a zero length period
  wire [7:0]  divider_reload = {5'b00000, rate_select_i} + 8'd3;
  wire        lfsr_feedback = lfsr_reg[14] ^ lfsr_reg[13];
  wire [14:0] lfsr_next = {lfsr_reg[13:0], lfsr_feedback};

  always @(posedge clk_i or negedge rst_ni) begin : noise_state_ff
    if (!rst_ni) begin
      lfsr_reg <= 15'h0001;
      divider_reg <= 8'd0;
    end else if (clear_enable_i) begin
      lfsr_reg <= 15'h0001;
      divider_reg <= 8'd0;
    end else if (!noise_enable_i) begin
      divider_reg <= divider_reload;
    end else if (divider_reg == 8'd0) begin
      divider_reg <= divider_reload;

      // Keep the LFSR from falling into the all zero state
      if (lfsr_next == 15'h0000) begin
        lfsr_reg <= 15'h0001;
      end else begin
        lfsr_reg <= lfsr_next;
      end
    end else begin
      divider_reg <= divider_reg - 8'd1;
    end
  end

  assign noise_bit_o = lfsr_reg[0];
  assign noise_sample_o = noise_enable_i ?
      (noise_bit_o ? NOISE_AMPLITUDE : -NOISE_AMPLITUDE) : 8'sd0;

endmodule // noise_generator

`default_nettype wire
