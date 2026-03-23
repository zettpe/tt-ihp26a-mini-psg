// SPDX-License-Identifier: Apache-2.0
/*
 * File   : phase_accumulator.v
 * Author : Peter Szentkuti
 *
 * Phase accumulator
 *
 * Stores the running phase for one tone channel. Reset and clear force
 * phase_value_o to zero. The phase advances only when advance_en_i and
 * gate_en_i are both high:
 *
 * phase_value_o <= 0 on reset or clear
 * phase_value_o <= phase_value_o + phase_step_i when advance_en_i and gate_en_i = 1
 */

`default_nettype none

module phase_accumulator (
  input  wire        clk_i,
  input  wire        rst_ni,
  input  wire        clear_enable_i,
  input  wire        advance_en_i,
  input  wire        gate_en_i,
  input  wire [22:0] phase_step_i,
  output reg  [22:0] phase_value_o
);

  // Clear the phase on reset or clear and advance it only when both enables are high
  always @(posedge clk_i or negedge rst_ni) begin : phase_value_ff
    if (!rst_ni) begin
      phase_value_o <= 23'd0;
    end else if (clear_enable_i) begin
      phase_value_o <= 23'd0;
    end else if (advance_en_i && gate_en_i) begin
      phase_value_o <= phase_value_o + phase_step_i;
    end
  end

endmodule // phase_accumulator
