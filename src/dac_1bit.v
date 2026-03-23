// SPDX-License-Identifier: Apache-2.0
/*
 * File   : dac_1bit.v
 * Author : Peter Szentkuti
 *
 * 1 bit audio output
 *
 * Turns the mixed sample into a delta sigma bit stream. Keeps the leftover
 * difference in error_reg, adds it to the new sample and uses the sign of
 * the sum to choose the next output bit.
 * The feedback levels are +255 and -256:
 *
 * sum_wide = error_reg + sample_in_i
 * audio_next = 1 when sum_wide >= 0, else 0
 * feedback_level = +255 when audio_next = 1, else -256
 * audio_o <= audio_next
 * error_reg <= sum_wide - feedback_level
 */

`default_nettype none
`timescale 1ns / 1ps

module dac_1bit (
  input  wire              clk_i,
  input  wire              rst_ni,
  input  wire              clear_enable_i,
  input  wire signed [8:0] sample_in_i,
  output reg               audio_o
);

  localparam signed [10:0] FEEDBACK_HIGH = 11'sd255;
  localparam signed [10:0] FEEDBACK_LOW = -11'sd256;

  reg  signed [10:0] error_reg;
  wire signed [10:0] sample_wide = {{2{sample_in_i[8]}}, sample_in_i};
  wire signed [10:0] sum_wide = error_reg + sample_wide;
  wire               audio_next = (sum_wide >= 11'sd0);
  wire signed [10:0] feedback_level = audio_next ? FEEDBACK_HIGH : FEEDBACK_LOW;

  // Register the next output bit and the new residual value, or clear both
  // to the idle state when clear_enable_i is high
  always @(posedge clk_i or negedge rst_ni) begin : dac_state_ff
    if (!rst_ni) begin
      error_reg <= 11'sd0;
      audio_o <= 1'b0;
    end else if (clear_enable_i) begin
      error_reg <= 11'sd0;
      audio_o <= 1'b0;
    end else begin
      audio_o <= audio_next;
      error_reg <= sum_wide - feedback_level;
    end
  end

endmodule // dac_1bit

`default_nettype wire
